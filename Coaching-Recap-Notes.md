# Coaching Recap Notes
*Weekly log of study progress — separate from the build/coaching bridge log (MCATai-Running-Notes.md). This one tracks what's been taught, what's solid, and what needs review before interviews. Update at the end of each study week and re-upload to Project Knowledge.*

**Format per week:** topics covered → what clicked immediately → what needed correction → open follow-ups to revisit before interview prep weeks (9–12).

---

## Week 1 — Web Stack Fluency (Track A)

**Topics covered:** TypeScript (interface vs type, generics, async typing) · Python async/await fundamentals · React hooks (useState, useEffect, useContext) · Next.js Server vs. Client Components + streaming · Supabase RLS

**What clicked immediately:**
- Async blocking-thread-at-scale reasoning — correct and confident on first answer
- `type` vs `interface` distinction — self-corrected to the fuller "type can alias/combine, not just enumerate" version well
- RLS as defense-in-depth (not just "where the check lives") — got there with one clarifying pass

**What needed correction:**
- Initial framing of *why* a component must be a Client Component conflated "where the streaming data comes from" with "which hooks require client-side execution." Corrected: it's `useState`/`useEffect` requiring a browser runtime, not the data source, that forces the Client Component boundary. Worth re-confirming this distinction cold before interviews — it's a common gotcha question.
- First answer on the RLS risk question inverted cause/effect (said the bug "breaks RLS" rather than "RLS is what catches the bug"). Corrected on same exchange — reframe as defense-in-depth if asked again.

**Open follow-ups for interview-prep weeks:**
- Re-drill the Server/Client Component boundary rule cold, no hints
- Re-drill "why RLS over middleware-only" as a from-scratch answer, not multiple choice

---

## Week 2 — AI Core Concepts, Track B (Weeks 1–2 of 4: Foundations)

**Topics covered:** Tokens & context windows · attention (conceptual, no math) · embeddings & cosine similarity · RAG pipeline end-to-end (chunking → embed/store → retrieval → reranking → generation) · naive-RAG failure modes (stale context, lost-in-the-middle, query mismatch) · diagnosing wrong answers via RAGAS (context precision/recall vs. faithfulness)

**What clicked immediately:**
- Correctly identified the high-level split: wrong answer = either a retrieval problem or a generation problem
- Grasped the RAG pipeline steps and why naive RAG fails without prompting

**What needed correction:**
- First diagnostic answer was a logical deduction ("if chunks return correctly, must be generation") rather than naming actual instrumentation. Corrected to the real workflow: pull the Langfuse trace, check retrieved chunks against RAGAS context precision/recall, then use faithfulness scoring to isolate a generation-only failure. Interviewers want to hear the *tooling*, not just the logic — worth re-drilling as a from-scratch answer.

**Open follow-ups for interview-prep weeks:**
- Re-drill the retrieval-vs-generation diagnostic flow cold, naming RAGAS metrics unprompted

**RESOLVED (follow-up session):** consistently-low faithfulness across many queries → correctly reasoned to corpus coverage gap (model answers beyond what retrieved context supports, falls back on parametric knowledge). Sharpened for interview delivery: tie faithfulness back to context recall on the *same* queries to show it's diagnosed, not guessed — "low faithfulness + low context recall together = corpus coverage gap." Second cause flagged for awareness: prompt template not explicitly instructing the model to refuse/hedge on insufficient context — strong answers name both, not just one.

---

## Week 3 — AI Core Concepts, Track B (Weeks 3–4 of 4: Agent Patterns, part 1)

**Topics covered:** ReAct loop · planner-executor · supervisor/orchestrator (mapped directly to NEXUS) · tool use/function calling (intro) · MCP (intro) · memory architecture taxonomy (working/episodic/semantic/procedural) mapped against MCATai's actual 4-tier model · ANN vs. exact nearest-neighbor tradeoff for episodic memory retrieval

**What clicked immediately:**
- Supervisor/orchestrator rationale — gave all four correct reasons unprompted (delegation, scalability, token efficiency, hallucination reduction) before any hints
- ANN vs. exact search tradeoff — correctly identified speed/scalability vs. accuracy on first answer

**What needed correction:**
- None this session — both major answers (orchestrator rationale, ANN tradeoff) were correct on the first pass; only added sharpening detail (instruction-following degradation as the mechanism behind "less hallucination"; index-structure explanation for *why* ANN scales) rather than correcting an error

**Memory tier mapping (for reference — MCATai's actual implementation):**
- Working Memory (Redis) → working memory ✓ clean match
- Episodic Memory (Mem0 + pgvector) → episodic memory ✓ clean match
- Domain Knowledge (LlamaIndex + pgvector) → semantic memory ✓ clean match, also doubles as the RAG pipeline
- Student Profile (Supabase) → blend of procedural (mastery/learning-style/emotional patterns) + semantic (static facts like test date/score goal) — deliberately not split into separate stores since always fetched together at session start; this nuance is itself a good interview answer showing awareness of where the textbook taxonomy diverges from a practical implementation

**Open follow-ups for interview-prep weeks:**
- None outstanding from this session — track progress on remaining Track B material (tool use/MCP deep dive, multi-agent handoff design specifics, then Weeks 5–8: eval/safety and production/scale)

---

## Week 4 — AI Core Concepts, Track B (Weeks 3–4 of 4: Agent Patterns, part 2)

**Topics covered:** Tool use/function calling mechanics (schema-based, model decides, app code executes) · why tool `description` quality drives correct tool selection · MCP as a standardized agent-tool interface (analogy: REST/OpenAPI for service-to-service, applied to agent-tool connections) · multi-agent handoff design in depth using ARIA→MIRA as the concrete case (trigger detection, context transfer, scope boundary)

**What clicked immediately:**
- Correctly identified that poor context transfer causes response repetition (ARIA/MIRA overlap)
- General instinct that personalization matters was directionally right from the start

**What needed correction:**
- Answers stayed at the level of general principle ("feels broken," "users need to feel personal") rather than naming the specific mechanism in MCATai's own architecture. Took three prompts to get to the concrete version: without ARIA's session_notes + student profile, MIRA can still detect frustration and respond supportively, but can't personalize — response becomes generic/interchangeable instead of acknowledging the specific stuck point (e.g., "4 attempts on inhibitor-type questions"). This generic-vs-specific distinction is the interview-ready framing; practice stating it directly and specifically next time, not building up to it through hints.

**Open follow-ups for interview-prep weeks:**
- Re-drill the handoff-failure-mode question cold: state the *specific* mechanism (loses ability to personalize, not just "feels broken") on the first pass, unprompted
- General pattern to watch: answers tend to start at the right general principle but need pushing to get to the concrete, architecture-specific version — practice going straight to specifics in future sessions

**Status:** Track B Weeks 1–4 (Foundations + Agent Patterns) complete. Weeks 5–6 (Evaluation & Safety — LLM-as-judge, RAGAS in depth, guardrails, HITL) picked up next, after a build session on P5 of MCATai.

---
