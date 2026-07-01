"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { dictionaries, type Language } from "@/i18n";
import type { ChatMessage, ChatResponse, Turn } from "@/lib/types";

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function ResultTable({ rows, noRowsLabel }: { rows: ChatResponse["rows"]; noRowsLabel: string }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">{noRowsLabel}</p>;
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="rounded-lg border">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead key={column}>{column}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={index}>
              {columns.map((column) => (
                <TableCell key={column}>{formatCell(row[column])}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function AssistantMessage({
  message,
  labels,
}: {
  message: Extract<ChatMessage, { role: "assistant" }>;
  labels: { showSql: string; noRows: string };
}) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border p-4 text-sm whitespace-pre-wrap">
        {message.content}
      </div>

      {message.sql && (
        <Collapsible className="space-y-2">
          <CollapsibleTrigger asChild>
            <Button variant="outline" size="sm">
              {labels.showSql}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-3">
            <pre className="overflow-x-auto rounded-lg border bg-muted p-4 text-xs">
              {message.sql}
            </pre>
            <ResultTable rows={message.rows} noRowsLabel={labels.noRows} />
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

export default function Home() {
  const [language, setLanguage] = useState<Language>("tr");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const t = dictionaries[language];

  async function submitQuestion(raw: string) {
    const trimmed = raw.trim();
    if (!trimmed || isLoading) return;

    // Prior turns become the history the backend seeds its conversation with.
    // Built from the messages already on screen, so it excludes this new question
    // (the backend appends that itself). Only role/content go — not sql/rows.
    const history: Turn[] = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    setError(null);
    setIsLoading(true);

    try {
      const httpResponse = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed, history }),
      });
      if (!httpResponse.ok) throw new Error("Request failed");

      const data: ChatResponse = await httpResponse.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sql: data.sql, rows: data.rows },
      ]);
    } catch {
      setError(t.error);
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: React.SyntheticEvent) {
    event.preventDefault();
    submitQuestion(question);
  }

  function handleExampleClick(example: string) {
    setQuestion(example);
    submitQuestion(example);
  }

  const showEmptyState = messages.length === 0 && !error && !isLoading;

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-6 px-4 py-12">
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-2xl font-semibold">{t.title}</h1>
          <div className="flex shrink-0 gap-1">
            {(["en", "tr"] as const).map((code) => (
              <Button
                key={code}
                variant={language === code ? "default" : "outline"}
                size="sm"
                onClick={() => setLanguage(code)}
              >
                {code.toUpperCase()}
              </Button>
            ))}
          </div>
        </div>
        <p className="text-sm text-muted-foreground">{t.description}</p>
      </header>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t.inputPlaceholder}
          disabled={isLoading}
        />
        <Button type="submit" disabled={isLoading || !question.trim()}>
          {isLoading ? t.askingButton : t.askButton}
        </Button>
      </form>

      {showEmptyState && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">{t.dataNote}</p>
          <div className="space-y-2">
            <p className="text-sm font-medium">{t.examplesHeading}</p>
            <div className="flex flex-col gap-2">
              {t.examples.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => handleExampleClick(example)}
                  className="rounded-lg border px-4 py-2 text-left text-sm transition-colors hover:bg-muted"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {messages.length > 0 && (
        <div className="space-y-6">
          {messages.map((message, index) =>
            message.role === "user" ? (
              <p key={index} className="text-sm font-medium">
                {message.content}
              </p>
            ) : (
              <AssistantMessage
                key={index}
                message={message}
                labels={{ showSql: t.showSql, noRows: t.noRows }}
              />
            ),
          )}
        </div>
      )}

      {isLoading && <p className="text-sm text-muted-foreground">{t.askingButton}</p>}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </main>
  );
}
