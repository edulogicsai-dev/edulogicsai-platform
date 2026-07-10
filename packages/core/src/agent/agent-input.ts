import type { ContentChunk, EpisodicMemory, Message, StudentProfile } from './memory-types';

/**
 * Field names/casing match specs/domain/glossary.md's pre-existing AgentInput
 * entry (source of truth), not a fresh design — see SPEC.md FR1.
 */
export interface AgentInput {
  tenant_id: string;
  student_id: string;
  session_id: string;
  message: string;
  student_profile: StudentProfile;
  session_history: Message[];
  retrieved_chunks: ContentChunk[];
  episodic_context: EpisodicMemory[];
}
