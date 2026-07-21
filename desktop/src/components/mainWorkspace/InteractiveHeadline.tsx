import { useEffect, useRef, useState } from "react";

function ReelLine({
  text,
  tone,
}: {
  text: string;
  tone: "static" | "incoming" | "outgoing";
}) {
  return (
    <span className={`reel-line is-${tone}`} aria-hidden={tone !== "static"}>
      {Array.from(text).map((character, index) => (
        <span
          key={`${tone}-${character}-${index}`}
          className="reel-char"
          style={{ ["--reel-i" as string]: index }}
        >
          {character === " " ? "\u00a0" : character}
        </span>
      ))}
    </span>
  );
}

export function InteractiveHeadline({ text }: { text: string }) {
  const [current, setCurrent] = useState(text);
  const [outgoing, setOutgoing] = useState<string | null>(null);
  const currentRef = useRef(text);

  useEffect(() => {
    if (text === currentRef.current) return;

    const previous = currentRef.current;
    currentRef.current = text;
    setOutgoing(previous);
    setCurrent(text);

    const staggerMs = 22;
    const duration = 380 + Math.max(previous.length, text.length) * staggerMs;
    const done = window.setTimeout(() => setOutgoing(null), duration);
    return () => window.clearTimeout(done);
  }, [text]);

  return (
    <h1 className="interactive-headline" aria-label={text}>
      <span className={`headline-reel ${outgoing ? "is-animating" : ""}`}>
        {outgoing ? (
          <>
            <ReelLine text={current} tone="incoming" />
            <ReelLine text={outgoing} tone="outgoing" />
          </>
        ) : (
          <ReelLine text={current} tone="static" />
        )}
      </span>
    </h1>
  );
}
