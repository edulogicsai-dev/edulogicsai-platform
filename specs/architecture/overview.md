# Architecture Overview — EduLogicsAI Platform

## Design Principle
Domain as Config, not Code. All domain-specific behaviour lives in DomainConfig.
Platform code has zero if-statements for domain logic.

## 8-Layer Architecture

### L0 — Client Tier
- Next.js 14 web app (Vercel)
- Expo SDK 55 React Native mobile app
- Domain theming via CSS custom properties from DomainConfig.theme
- Agent roster loaded from DomainConfig.agents (not hardcoded)
- SSE streaming for real-time agent responses

### L1 — API Gateway & Auth
- Vercel Edge Middleware (JWT validation, tenant resolution from subdomain)
- LiteLLM Gateway (unified LLM interface, model routing, prompt caching)
- Domain Router (reads tenant header → loads DomainConfig)
- Rate limiter (Upstash Redis, per-tenant per-student)

### L2 — Orchestration Layer
- NEXUS supervisor agent (domain-agnostic, reads DomainConfig.agents)
- LangGraph state machine (one node per agent, edges = handoff conditions)
- Session Manager (Redis, working memory, TTL 30min)
- HITL Escalation Bus (Tier 1 auto / Tier 2 flagged / Tier 3 live human)

### L3 — Agent Fleet
- BaseAgent abstract class (respond, stream, handoff_check, memory_write)
- Domain Agent Registry (Dict[tenant_id → List[AgentClass]])
- Tool Registry via MCP (RAGTool, SentimentTool, CalendarTool, QuestionBankTool)
- Prompt Registry (Langfuse, version-controlled, A/B testable)

### L4 — Memory & Knowledge
- Tier 1: Working Memory (Redis, per session, last 10 turns)
- Tier 2: Episodic Memory (Mem0 + pgvector, session summaries)
- Tier 3: Domain Knowledge (LlamaIndex + pgvector, per-tenant namespace)
- Tier 4: Student Profile (Supabase, mastery levels, FSRS next_review)

### L5 — Self-Improvement Engine
- EVAL Agent (LLM-as-Judge via Haiku Batch API, nightly 5% sample)
- Ragas RAG Evaluator (faithfulness + context recall scoring)
- Prompt Evolution Pipeline (eval → human review → A/B test → auto-rollout)
- Content Refresh (Firecrawl monitors domain sources, LlamaIndex re-index)

### L6 — Observability & Governance
- Langfuse (self-hosted on Railway, traces every LLM call)
- PostHog (product analytics, feature flags, session recording)
- AI Governance (risk classification, distress signal log, audit trail)
- Cost Ledger (per-tenant per-student API cost tracking)

### L7 — Infrastructure & Data Platform
- Supabase (multi-tenant Postgres + pgvector + Auth + RLS)
- Railway (FastAPI backend + background workers + Langfuse host)
- Vercel (Next.js web app, auto-deploy from GitHub)
- Turborepo monorepo (packages/core, ui, memory, eval + apps/web, mobile, backend)

## Data Flow — Happy Path
1. Student sends message → L0 Client
2. Edge validates JWT, resolves tenant → L1 Gateway
3. NEXUS classifies intent, selects agent → L2 Orchestration
4. Memory assembled (profile + episodic + RAG chunks) → L4 Memory
5. Agent generates response via LiteLLM → L3 Agent
6. Response streamed via SSE → L0 Client
7. Session notes written to episodic memory → L4 Memory
8. Langfuse trace + cost logged → L6 Observability

## Multi-Tenant Isolation
- tenant_id on every database row (NOT nullable)
- RLS policies enforce tenant_id = current_tenant()
- pgvector namespaces per domain (mcat_content vs gre_content)
- DomainConfig loaded per tenant at NEXUS boot
- Cross-tenant data access is impossible by construction
