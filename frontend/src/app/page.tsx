"use client";

import { useEffect, useRef, useState } from "react";

import { AboutDialog } from "@/components/chat/about-dialog";
import { AssistantBubble, TypingBubble, UserBubble } from "@/components/chat/chat-message";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { dictionaries, type Language } from "@/i18n";
import type { ChatMessage, ChatResponse, Turn } from "@/lib/types";

export default function Home() {
  const [language, setLanguage] = useState<Language>("tr");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const t = dictionaries[language];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

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

  const showEmptyState = messages.length === 0 && !error && !isLoading;
  const sqlLabels = { showSql: t.showSql, hideSql: t.hideSql, noRows: t.noRows };

  return (
    <div className="mx-auto flex h-dvh w-full max-w-3xl flex-col px-4">
      <header className="shrink-0 space-y-2 py-4 sm:py-6">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-xl font-semibold sm:text-2xl">{t.title}</h1>
          <div className="flex shrink-0 items-center gap-1">
            <AboutDialog
              triggerLabel={t.aboutButton}
              title={t.aboutTitle}
              body={t.aboutBody}
              srDescription={t.description}
            />
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

      <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto pb-4">
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
                    onClick={() => submitQuestion(example)}
                    className="rounded-lg border px-4 py-2 text-left text-sm transition-colors hover:bg-muted"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((message, index) =>
          message.role === "user" ? (
            <UserBubble key={index} content={message.content} />
          ) : (
            <AssistantBubble key={index} message={message} labels={sqlLabels} />
          ),
        )}

        {isLoading && <TypingBubble />}
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>

      <form onSubmit={handleSubmit} className="shrink-0 flex gap-2 border-t py-4">
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
    </div>
  );
}
