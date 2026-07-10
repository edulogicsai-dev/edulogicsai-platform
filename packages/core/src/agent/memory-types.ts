/**
 * Platform-level memory-tier types shared by AgentInput/AgentOutput.
 * These describe memory-tier shape (profile, working memory, RAG, episodic,
 * mastery), not domain content — no MCAT/GRE/DAT-specific fields belong here.
 */

export interface StudentProfile {
  userId: string;
  displayName: string;
  createdAt: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ContentChunk {
  id: string;
  text: string;
  sourceId: string;
  score: number;
}

export interface EpisodicMemory {
  id: string;
  summary: string;
  occurredAt: string;
  relevanceScore: number;
}

export interface MasteryDelta {
  conceptId: string;
  previousStability: number;
  newStability: number;
  reviewedAt: string;
}
