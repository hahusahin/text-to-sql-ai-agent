import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renders a markdown string with the app's prose styling.
 *
 * Shared by the assistant bubble (the model's answer) and the About dialog, so
 * the `prose` classes and the GitHub-flavored-markdown plugin live in one place. */
export function MarkdownContent({ children }: { children: string }) {
  return (
    <div className="prose prose-sm max-w-none dark:prose-invert prose-pre:my-0">
      <Markdown remarkPlugins={[remarkGfm]}>{children}</Markdown>
    </div>
  );
}
