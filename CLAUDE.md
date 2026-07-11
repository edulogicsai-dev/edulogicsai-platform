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
packages/core/    — BaseAgent/AgentInput/AgentOutput/DomainConfig CONTRACT TYPES (TypeScript only — no agent logic)
packages/ui/      — Shared React components (domain-themeable via CSS vars)
packages/memory/  — Mem0, pgvector helpers, FSRS spaced repetition
packages/eval/    — EVAL agent, Ragas pipeline, PromptRegistry client
apps/web/         — Next.js 14, domain theme via CSS custom properties
apps/mobile/      — Expo SDK 55 React Native
apps/backend/     — FastAPI, NEXUS, agent server (Python — see Agent Contract Architecture below), SSE streaming, background jobs
domains/mcat/     — DomainConfig + prompts (Python-side); 7 agent implementations live under apps/backend/domains/mcat/agents/
domains/gre/      — DomainConfig + prompts (Phase 2)
domains/dat/      — DomainConfig + prompts (Phase 2)
specs/            — SDD specs, one folder per feature

## Agent Contract Architecture (Hybrid TS/Python)
The BaseAgent/AgentInput/AgentOutput/DomainConfig contract exists in two forms that must stay shape-identical:
- **packages/core (TypeScript)** — the CONTRACT: type definitions only. Consumed by apps/web and apps/mobile to parse SSE streams and render agent responses. No agent logic here.
- **apps/backend (Python)** — the IMPLEMENTATION: actual agent logic (LLM calls via LiteLLM, RAG retrieval, sentiment analysis, handoff decisions), orchestrated by NEXUS via LangGraph, all running on FastAPI. Domain agent classes do NOT extend the TypeScript BaseAgent class (impossible across runtimes) — they conform to the same shape using Pydantic models that mirror AgentInput/AgentOutput field-for-field.
- SSE serializes Python AgentOutput → JSON → frontend parses with the TypeScript AgentOutput type. Any field change must be applied to both the TypeScript types and the Pydantic models in the same change.

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
- Agent implementation files: apps/backend/domains/{domain}/agents/{name}.py (Pydantic models mirror packages/core's TypeScript contract types)
- Agent contract types:       packages/core/src/agent/*.ts (shared across all domains, not per-domain)
- Prompt files:   domains/{domain}/prompts/{agent}_v1.md
- Spec files:     specs/{area}/{NAME}-SPEC.md
- DB migrations:  supabase/migrations/00N_description.sql
- Packages:       @mcatai/core, @mcatai/ui, @mcatai/memory, @mcatai/eval
