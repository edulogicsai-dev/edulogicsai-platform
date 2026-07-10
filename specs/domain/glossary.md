# Domain Glossary — EduLogicsAI Platform

## Core Concepts

| Term | Definition |
|------|------------|
| DomainConfig | JSON config defining a complete product: agents, content index, eval rubric, theme, escalation rules. One per domain. |
| Tenant | A domain product instance (mcat, gre, dat). Maps to tenant_id in every DB row. |
| BaseAgent | Abstract class all domain agents inherit. Defines respond(), stream(), fetchPrompt(), writeEpisodicMemory(). |
| NEXUS | Domain-agnostic supervisor agent. Reads DomainConfig.agents at boot. Routes student messages to the correct agent. |
| AgentInput | Immutable contract: student_id, session_id, tenant_id, message, student_profile, session_history, retrieved_chunks, episodic_context. |
| AgentOutput | Immutable contract: response, agent_id, cited_chunks, suggested_handoff, mastery_update, session_notes, risk_level. |
| AgentDef | One roster entry in `DomainConfig.agents` — id, display name, and a `createAgent()` factory NEXUS uses to instantiate a `BaseAgent` without importing the domain package directly. |
| DomainRegistry | packages/core-owned lookup: domain id → `DomainConfig`, agent id → `BaseAgent` instance. Populated via self-registration — each domain package calls `register()` on import. Contains zero imports from any domain package. |
| Handoff | When one agent suggests routing to another via AgentOutput.suggested_handoff. LangGraph transitions state. |
| PromptRegistry | Langfuse-hosted versioned system prompts per agent per domain. Fetched at runtime, never hardcoded. |
| EvalRubric | Domain-specific scoring weights (accuracy, pedagogy, safety, clarity) used by the EVAL agent. |
| ContentIndex | pgvector namespace holding domain knowledge chunks (e.g., mcat_content, gre_content). |

## MCAT Domain Agents

| Agent | Role |
|-------|------|
| ARIA | Adaptive Tutor — Socratic method, explains concepts across all MCAT sections |
| QUINN | Practice Questions — generates, curates, explains practice questions |
| SAGE | Deep Science — specialist for Bio/Biochem, Chem/Physics mechanisms |
| VERA | CARS & Verbal — critical analysis, passage deconstruction, argument mapping |
| MIRA | Motivation Coach — detects frustration/burnout, provides encouragement |
| SCOUT | Study Planner — generates/adjusts daily and weekly study plans using FSRS |
| ATLAS | Application Strategy — med school timeline, school selection, MCAT-in-context |

## Memory Tiers

| Tier | Store | Scope | TTL |
|------|-------|-------|-----|
| Working Memory | Redis | per session | 30 min |
| Episodic Memory | Mem0 + pgvector | per student per tenant | permanent |
| Domain Knowledge | LlamaIndex + pgvector | per tenant | permanent |
| Student Profile | Supabase | per student per tenant | permanent |

## Conventions
- Use singular nouns for entities (Student, Agent, Session)
- Concept IDs prefixed with domain: 'mcat::enzyme_kinetics'
- Agent IDs are lowercase: 'aria', 'quinn', 'sage'
- Tenant IDs are lowercase: 'mcat', 'gre', 'dat'
