import { Check, Copy } from 'lucide-react';
import { Fragment, useRef, useState } from 'react';

// One command, one line, one button. The button copies exactly the command, nothing else.
export default function CopyCommand({ command, size = 'md' }: { command: string; size?: 'md' | 'lg' }) {
  const [done, setDone] = useState(false);
  const timer = useRef<number>();

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      return;
    }
    setDone(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setDone(false), 1800);
    const ph = (window as unknown as { posthog?: { capture: (e: string, p: object) => void } }).posthog;
    ph?.capture('code_copy', { install: command.startsWith('npx skills add'), command, path: location.pathname });
  };

  return (
    <div className={`cmd cmd--${size}`}>
      <code>
        <span className="cmd__prompt" aria-hidden="true">$</span>
        {/* each word stays whole, so a narrow screen breaks between words, never inside the repo name */}
        {command.split(' ').map((word, i) => (
          <Fragment key={i}>
            {i > 0 && ' '}
            <span className="cmd__word">{word}</span>
          </Fragment>
        ))}
      </code>
      <button type="button" onClick={copy} className="cmd__btn" data-done={done || undefined} aria-label={done ? 'Copied' : 'Copy command'}>
        {done ? <Check size={16} strokeWidth={1.75} aria-hidden="true" /> : <Copy size={16} strokeWidth={1.5} aria-hidden="true" />}
        <span className="cmd__label">{done ? 'Copied' : 'Copy'}</span>
      </button>
      <span className="sr-only" aria-live="polite">{done ? 'Command copied' : ''}</span>
    </div>
  );
}
