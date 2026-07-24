import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import domains.mcat.domain_config  # noqa: F401 -- self-registration
from api.chat import create_chat_router
from auth.jwt_verifier import JWTVerifier
from db.pool import create_pool
from domains._contracts.domain_registry import registry
from nexus.graph_builder import build_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    # /api/chat requires a JWT secret and a database DSN. Neither is
    # available in this environment (see
    # changes/2026/07/17/nexus-orchestration/SPEC.md Requirements Discovery)
    # -- rather than crash app startup for every other test/dev use of this
    # FastAPI app, the router is simply not mounted when unconfigured.
    jwt_secret = os.environ.get("JWT_SECRET")
    dsn = os.environ.get("DATABASE_URL")
    if jwt_secret and dsn:
        pool = await create_pool(dsn)
        domain_result = registry.resolve_domain("mcat")
        graph = build_graph(domain_result.config, registry)
        router = create_chat_router(
            jwt_verifier=JWTVerifier(jwks_url="https://cvxtqcebikmqaskvewlm.supabase.co/auth/v1/.well-known/jwks.json", secret=jwt_secret),
            pool=pool,
            graph=graph,
            default_entry_agent_id="aria",
        )
        app.include_router(router)
    yield


app = FastAPI(title="EduLogicsAI Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "https://edulogicsai-platform.vercel.app", "https://mcatai-web.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
