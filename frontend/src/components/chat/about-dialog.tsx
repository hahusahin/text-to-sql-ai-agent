import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { MarkdownContent } from "@/components/chat/markdown-content";

/** Optional, button-triggered explainer: what the factory makes, what data is
 * behind the assistant, and what kinds of questions it can answer. Never opens
 * on its own — the visitor decides when they want the detail. */
export function AboutDialog({
  triggerLabel,
  title,
  body,
  srDescription,
}: {
  triggerLabel: string;
  title: string;
  body: string;
  srDescription: string;
}) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription className="sr-only">{srDescription}</DialogDescription>
        </DialogHeader>
        <MarkdownContent>{body}</MarkdownContent>
      </DialogContent>
    </Dialog>
  );
}
