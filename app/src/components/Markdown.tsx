import { Fragment } from "react";

/** Tiny renderer for our own docs (headings, paragraphs, lists, **bold**). Not for untrusted input. */
function inline(text: string) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) =>
    part.startsWith("**") ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : part.startsWith("`") ? (
      <code key={i}>{part.slice(1, -1)}</code>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  );
}

export function Markdown({ source, skipTitle = true }: { source: string; skipTitle?: boolean }) {
  const blocks = source.trim().split(/\n\n+/);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {blocks.map((b, i) => {
        if (b.startsWith("# ")) return skipTitle ? null : <h1 key={i}>{b.slice(2)}</h1>;
        if (b.startsWith("## ")) return <h2 key={i} style={{ fontSize: 20, marginTop: 8 }}>{b.slice(3)}</h2>;
        if (/^- /m.test(b))
          return (
            <ul key={i} style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 6 }}>
              {b.split(/\n(?=- )/).map((li, j) => (
                <li key={j}>{inline(li.replace(/^- /, ""))}</li>
              ))}
            </ul>
          );
        return (
          <p key={i} style={{ color: "var(--muted)" }}>
            {inline(b)}
          </p>
        );
      })}
    </div>
  );
}
