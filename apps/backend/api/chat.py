"""
POST /api/chat -- the endpoint students actually hit. See
changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/SPEC.md.

create_chat_router() is a factory, not a module-level router, so tests (and
main.py) can inject real-or-fake collaborators explicitly rather than
reaching for hidden global state.
"""

import datetime
import json
import logging
from typing import Optional

import asyncpg
from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from auth.jwt_verifier import InvalidTokenError, JWTVerifier
from db.live_agent_input import append_to_session_history, build_live_agent_input
from db.repositories import (
    AgentSessionRepository,
    DomainContentRepository,
    EpisodicMemoryRepository,
    StudentProfileRepository,
)
from domains._contracts.agent_io import Message
from nexus.turn_runner import run_turn

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    tenant_id: str


def create_chat_router(
    jwt_verifier: JWTVerifier,
    pool: asyncpg.Pool,
    graph: CompiledStateGraph,
    default_entry_agent_id: str,
) -> APIRouter:
    router = APIRouter()

    student_profile_repo = StudentProfileRepository(pool)
    episodic_repo = EpisodicMemoryRepository(pool)
    content_repo = DomainContentRepository(pool)
    session_repo = AgentSessionRepository(pool)

    @router.post("/api/chat")
    async def chat(request: ChatRequest, authorization: Optional[str] = Header(None)):
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")

        token = authorization[len("Bearer ") :]
        try:
            user_id = jwt_verifier.verify(token)
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        # FR3: tenant membership -- student_profiles' (user_id, tenant_id)
        # composite key IS the membership record; no new table needed.
        try:
            await student_profile_repo.load_profile(tenant_id=request.tenant_id, user_id=user_id)
        except ValueError:
            raise HTTPException(status_code=403, detail="Not a member of this tenant")

        # FR4: session resolution
        if request.session_id is None:
            session_id = await session_repo.create_session(
                tenant_id=request.tenant_id, student_id=user_id, agent_id=default_entry_agent_id
            )
        else:
            session_id = request.session_id
            await session_repo.increment_turn_count(
                session_id=session_id, tenant_id=request.tenant_id, student_id=user_id
            )

        append_to_session_history(
            session_id,
            Message(
                role="user",
                content=request.message,
                timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )

        async def event_stream():
            try:
                agent_input = await build_live_agent_input(
                    tenant_id=request.tenant_id,
                    student_id=user_id,
                    session_id=session_id,
                    message=request.message,
                    student_profile_repo=student_profile_repo,
                    episodic_repo=episodic_repo,
                    content_repo=content_repo,
                )
                result = await run_turn(
                    graph,
                    session_id=session_id,
                    agent_input=agent_input,
                    default_entry_agent_id=default_entry_agent_id,
                )
                for output in result.outputs:
                    yield f"event: message\ndata: {output.model_dump_json()}\n\n"
                yield "event: done\ndata: \n\n"
            except Exception:
                # FR6: graceful SSE error, not a raw 500 or a dropped connection.
                logger.exception("Error processing chat turn (session_id=%s)", session_id)
                payload = json.dumps({"error": "Something went wrong processing your message."})
                yield f"event: error\ndata: {payload}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    return router
