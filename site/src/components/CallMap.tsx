import * as ToggleGroup from '@radix-ui/react-toggle-group';
import { animate, stagger } from 'animejs';
import { ArrowRight, BadgeCheck, Ear, Gauge, MessageSquareText, Phone, Workflow } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

type Skill = { name: string; title: string; decides: string; useWhen: string };

// One call, left to right. Each skill sits at the part of the call it governs.
const STAGES = [
  { id: 'build', label: 'Pipeline', Icon: Workflow, names: ['voice-pipeline-choice', 'voice-full-duplex'] },
  { id: 'listen', label: 'Listening', Icon: Ear, names: ['voice-turn-taking', 'voice-interruptions'] },
  { id: 'speak', label: 'Speaking and acting', Icon: MessageSquareText, names: ['voice-prompting', 'voice-function-tools'] },
  { id: 'speed', label: 'Speed', Icon: Gauge, names: ['voice-latency-budget'] },
  { id: 'phone', label: 'Phone line', Icon: Phone, names: ['voice-telephony'] },
  { id: 'prove', label: 'Proof', Icon: BadgeCheck, names: ['voice-agent-evals', 'voice-agent-review'] },
] as const;

export default function CallMap({ skills }: { skills: Skill[] }) {
  const [stage, setStage] = useState<string>('listen');
  const list = useRef<HTMLUListElement>(null);
  const byName = Object.fromEntries(skills.map((s) => [s.name, s]));
  const current = STAGES.find((s) => s.id === stage) ?? STAGES[1];

  useEffect(() => {
    if (!list.current || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    animate(list.current.querySelectorAll('li'), { opacity: [0, 1], y: [8, 0], duration: 480, ease: 'outExpo', delay: stagger(70) });
  }, [stage]);

  return (
    <div className="callmap">
      <ToggleGroup.Root
        type="single"
        value={stage}
        onValueChange={(v) => v && setStage(v)}
        aria-label="Parts of a call"
        className="callmap__stages"
      >
        {STAGES.map(({ id, label, Icon }, i) => (
          <ToggleGroup.Item key={id} value={id} className="callmap__stage" aria-label={label}>
            <span className="callmap__dot">
              <Icon size={18} strokeWidth={1.5} aria-hidden="true" />
            </span>
            <span className="callmap__label">{label}</span>
            {i < STAGES.length - 1 && <span className="callmap__wire" aria-hidden="true" />}
          </ToggleGroup.Item>
        ))}
      </ToggleGroup.Root>
      <ul ref={list} className="callmap__skills" aria-live="polite">
        {current.names
          .map((n) => byName[n])
          .filter(Boolean)
          .map((s) => (
            <li key={s.name}>
              <a href={`/skills/${s.name}/`}>
                <code>{s.name}</code>
                <span>{s.useWhen}</span>
                <ArrowRight size={18} strokeWidth={1.5} aria-hidden="true" className="callmap__go" />
              </a>
            </li>
          ))}
      </ul>
    </div>
  );
}
