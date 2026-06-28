/** Mirrors the backend `ChatResponse` (backend/app/models/chat.py). */
export type ChatResponse = {
  answer: string;
  sql: string;
  rows: Record<string, unknown>[];
};
