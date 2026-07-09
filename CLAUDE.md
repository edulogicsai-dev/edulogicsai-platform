# EduLogicsAI Platform — Claude Code Memory

## What we are building
Generic, domain-agnostic AI tutoring platform.
MCATai is the reference implementation.
GREai, DATai extend via DomainConfig — zero platform code changes.

## Repo
GitHub: github.com/edulogicsai-dev/edulogicsai-platform
Branch: main
Vercel: edulogicsai-platform.vercel.app

## Supabase
Project: edulogicsai
Region:  us-east-1
URL:     https://cvxtqcebikmqaskvewlm.supabase.co

## Monorepo Structure
packages/core/    — BaseAgent, NEXUS, DomainRegistry, contracts
packages/ui/      — Shared React components (domain-themeable via CSS vars)
packages/memory/  — Mem0, pgvector helpers, FSRS spaced repetition
packages/eval/    — EVAL agent, Ragas pipeline, PromptRegistry client
apps/web/         — Next.js 14, domain theme via CSS custom properties
apps/mobile/      — Expo SDK 55 React Native
apps/backend/     — FastAPI, agent server, SSE streaming, background jobs
domains/mcat/     — DomainConfig + 7 agent subclasses + prompts
domains/gre/      — DomainConfig + 5 agents (Phase 2)
domains/dat/      — DomainConfig + 6 agents (Phase 2)
specs/            — SDD specs, one folder per feature

## Tech Stack
Frontend Web:    Next.js 14, TypeScript, Tailwind, shadcn/ui
Frontend Mobile: Expo SDK 55, React Native, TypeScript
Backend:         FastAPI (Python 3.11+), Railway
Database:        Supabase (Postgres + pgvector + Auth + RLS)
Agents:          Claude Agent SDK, LangGraph
Memory:          Mem0 (episodic), LlamaIndex + pgvector (knowledge RAG)
LLM Gateway:     LiteLLM (routing, caching, cost tracking)
Observability:   Langfuse (self-hosted on Railway)
Payments:        Stripe
Spaced Rep:      ts-fsrs (FSRS-5 algorithm)
Eval:            Ragas + LLM-as-Judge via Batch API

## Architecture Rules — NEVER violate
- DomainConfig is the ONLY place domain-specific logic lives
- All LLM calls route through LiteLLM — never direct Anthropic SDK
- tenant_id + user_id MUST scope every DB query (RLS enforced)
- Agent responses ALWAYS streamed via SSE — never blocking JSON
- Prompts NEVER hardcoded — always from PromptRegistry (Langfuse)
- service_role key NEVER in any NEXT_PUBLIC_ env var
- BaseAgent contract (AgentInput/AgentOutput) is immutable
- NEXUS contains zero domain-specific logic

## DomainConfig Schema (all domains implement this)
interface DomainConfig {
  id: string              // 'mcat' | 'gre' | 'dat'
  name: string            // 'MCATai'
  subdomain: string       // 'app.mcatai.co'
  agents: AgentDef[]      // roster loaded by NEXUS at boot
  contentIndex: string    // pgvector namespace 'mcat_content'
  evalRubric: EvalRubric  // domain-specific scoring weights
  theme: ThemeVars        // CSS custom properties only
  escalationRules: Rule[] // HITL thresholds
}

## SDD Rules
- status: draft → approved before /sdd implement runs
- Every spec has Given/When/Then acceptance criteria
- /sdd verify after every feature
- Prompts in PromptRegistry (Langfuse), never in source files
- Specs: specs/{area}/{NAME}-SPEC.md

## Naming Conventions
- Agent files:    domains/{domain}/agents/{name}.py
- Prompt files:   domains/{domain}/prompts/{agent}_v1.md
- Spec files:     specs/{area}/{NAME}-SPEC.md
- DB migrations:  supabase/migrations/00N_description.sql
- Packages:       @mcatai/core, @mcatai/ui, @mcatai/memory, @mcatai/eval
