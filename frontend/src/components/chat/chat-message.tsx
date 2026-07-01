"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { MarkdownContent } from "@/components/chat/markdown-content";
import { ResultTable } from "@/components/chat/result-table";
import type { ChatMessage } from "@/lib/types";

export type SqlLabels = { showSql: string; hideSql: string; noRows: string };

/** A question the user asked — right-aligned bubble. */
export function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm whitespace-pre-wrap text-primary-foreground">
        {content}
      </div>
    </div>
  );
}

/** The model's answer — left-aligned bubble, with the SQL/result behind a toggle. */
export function AssistantBubble({
  message,
  labels,
}: {
  message: Extract<ChatMessage, { role: "assistant" }>;
  labels: SqlLabels;
}) {
  const [sqlOpen, setSqlOpen] = useState(false);

  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[90%] space-y-3 rounded-2xl rounded-bl-sm bg-muted px-4 py-3">
        <MarkdownContent>{message.content}</MarkdownContent>

        {message.sql && (
          <Collapsible open={sqlOpen} onOpenChange={setSqlOpen} className="space-y-2">
            <CollapsibleTrigger asChild>
              <Button variant="outline" size="sm">
                {sqlOpen ? labels.hideSql : labels.showSql}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="space-y-3">
              <pre className="overflow-x-auto rounded-lg border bg-background p-4 text-xs">
                {message.sql}
              </pre>
              <ResultTable rows={message.rows} noRowsLabel={labels.noRows} />
            </CollapsibleContent>
          </Collapsible>
        )}
      </div>
    </div>
  );
}

/** The "thinking" placeholder shown while the agent is working. */
export function TypingBubble() {
  return (
    <div className="flex justify-start">
      <div className="flex gap-1 rounded-2xl rounded-bl-sm bg-muted px-4 py-4">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
