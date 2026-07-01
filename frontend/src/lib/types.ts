/** Mirrors the backend `ChatResponse` (backend/app/models/chat.py). */
export type ChatResponse = {
  answer: string;
  sql: string;
  rows: Record<string, unknown>[];
};

/** One prior turn sent back to the backend as context (mirrors `Turn`). */
export type Turn = {
  role: "user" | "assistant";
  content: string;
};

/** A message rendered in the thread. Both variants carry `content` so the
 * conversation history can be built uniformly; the assistant variant also keeps
 * the SQL/rows behind its answer for the expandable proof disclosure. */
export type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; sql: string; rows: ChatResponse["rows"] };
