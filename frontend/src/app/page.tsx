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
import type { ChatResponse } from "@/lib/types";

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

export default function Home() {
  const [language, setLanguage] = useState<Language>("tr");
  const [question, setQuestion] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const t = dictionaries[language];

  async function submitQuestion(raw: string) {
    const trimmed = raw.trim();
    if (!trimmed || isLoading) return;

    setIsLoading(true);
    setError(null);
    setResponse(null);

    try {
      const httpResponse = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed }),
      });
      if (!httpResponse.ok) throw new Error("Request failed");

      const data: ChatResponse = await httpResponse.json();
      setResponse(data);
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

  const showEmptyState = !response && !error && !isLoading;

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

      {error && <p className="text-sm text-destructive">{error}</p>}

      {response && (
        <div className="space-y-4">
          <div className="rounded-lg border p-4 text-sm whitespace-pre-wrap">
            {response.answer}
          </div>

          {response.sql && (
            <Collapsible className="space-y-2">
              <CollapsibleTrigger asChild>
                <Button variant="outline" size="sm">
                  {t.showSql}
                </Button>
              </CollapsibleTrigger>
              <CollapsibleContent className="space-y-3">
                <pre className="overflow-x-auto rounded-lg border bg-muted p-4 text-xs">
                  {response.sql}
                </pre>
                <ResultTable rows={response.rows} noRowsLabel={t.noRows} />
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      )}
    </main>
  );
}
