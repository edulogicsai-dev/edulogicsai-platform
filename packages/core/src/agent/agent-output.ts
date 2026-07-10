import type { MasteryDelta } from './memory-types';

export type RiskLevel = 'low' | 'medium' | 'high';

export interface AgentOutput {
  response: string;
  agent_id: string;
  cited_chunks: string[];
  suggested_handoff: string | null;
  mastery_update: MasteryDelta | null;
  session_notes: string;
  risk_level: RiskLevel;
}
