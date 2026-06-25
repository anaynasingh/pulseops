import { Fragment, type ReactNode } from "react";

/**
 * Lightweight markdown renderer for AI assistant messages.
 *
 * The assistant (GPT-4o) replies in constrained markdown: bold spans
 * (`**text**`), bullet lists (`-`/`*`, optionally nested by indentation),
 * and plain paragraphs. Rendering `{content}` directly collapsed newlines
 * and showed raw `-`/`**` syntax. This parses that subset into readable
 * block elements while staying dependency-free.
 */

/** Parse inline markdown (`**bold**`) into React nodes. */
function renderInline(text: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    const bold = part.match(/^\*\*([^*]+)\*\*$/);
    if (bold) {
      return (
        <strong key={i} className="font-semibold text-slate-100">
          {bold[1]}
        </strong>
      );
    }
    return <Fragment key={i}>{part}</Fragment>;
  });
}

interface ListItem {
  text: string;
  depth: number;
}

const BULLET_RE = /^(\s*)[-*]\s+(.*)$/;

export function ChatMarkdown({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let listBuffer: ListItem[] = [];

  const flushList = () => {
    if (listBuffer.length === 0) return;
    const items = listBuffer;
    listBuffer = [];
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="space-y-1">
        {items.map((item, i) => (
          <li
            key={i}
            className="flex gap-1.5"
            style={{ marginLeft: item.depth > 0 ? item.depth * 12 : 0 }}
          >
            <span className="text-indigo-400 shrink-0 leading-relaxed">
              {item.depth > 0 ? "◦" : "•"}
            </span>
            <span className="flex-1">{renderInline(item.text)}</span>
          </li>
        ))}
      </ul>
    );
  };

  for (const line of lines) {
    const bullet = line.match(BULLET_RE);
    if (bullet) {
      const indent = bullet[1].replace(/\t/g, "  ").length;
      listBuffer.push({ text: bullet[2].trim(), depth: indent >= 2 ? 1 : 0 });
      continue;
    }

    flushList();

    if (line.trim() === "") continue;

    blocks.push(
      <p key={`p-${blocks.length}`} className="leading-relaxed">
        {renderInline(line.trim())}
      </p>
    );
  }

  flushList();

  return <div className="space-y-1.5">{blocks}</div>;
}
