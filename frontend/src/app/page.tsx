"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ChatResponse } from "@/lib/types";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(event: React.SyntheticEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || isLoading) return;

    setIsLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      if (!response.ok) throw new Error("Request failed");

      const data: ChatResponse = await response.json();
      setAnswer(data.answer);
    } catch {
      setError("Something went wrong. Is the AI service running?");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-12">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold">Manufacturing Text-to-SQL Assistant</h1>
        <p className="text-sm text-muted-foreground">
          Ask a plain-language question about the factory&apos;s production, downtime, and quality
          data.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="e.g. How many production lines are there?"
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading || !question.trim()}>
          {isLoading ? "Asking…" : "Ask"}
        </Button>
      </form>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {answer && (
        <div className="rounded-lg border p-4 text-sm whitespace-pre-wrap">{answer}</div>
      )}
    </main>
  );
}
