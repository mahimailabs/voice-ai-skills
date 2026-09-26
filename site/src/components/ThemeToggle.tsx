import * as ToggleGroup from '@radix-ui/react-toggle-group';
import { Monitor, Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

// Starlight's theme contract: the choice lives in localStorage['starlight-theme'] ('' means
// auto) and the applied theme on <html data-theme>. ThemeProvider.astro reads it before paint.
type Choice = 'light' | 'dark' | 'auto';
const KEY = 'starlight-theme';
const media = () => window.matchMedia('(prefers-color-scheme: light)');
const apply = (c: Choice) => {
  const theme = c === 'auto' ? (media().matches ? 'light' : 'dark') : c;
  document.documentElement.dataset.theme = theme;
};

export default function ThemeToggle() {
  const [choice, setChoice] = useState<Choice>('dark');

  useEffect(() => {
    const stored = localStorage.getItem(KEY);
    setChoice(stored === 'light' || stored === 'dark' ? stored : 'auto');
  }, []);

  useEffect(() => {
    if (choice !== 'auto') return;
    const m = media();
    const onChange = () => apply('auto');
    m.addEventListener('change', onChange);
    return () => m.removeEventListener('change', onChange);
  }, [choice]);

  const select = (value: string) => {
    if (!value) return; // clicking the active item keeps it selected
    const c = value as Choice;
    localStorage.setItem(KEY, c === 'auto' ? '' : c);
    apply(c);
    setChoice(c);
  };

  const items: { value: Choice; label: string; Icon: typeof Sun }[] = [
    { value: 'light', label: 'Light theme', Icon: Sun },
    { value: 'dark', label: 'Dark theme', Icon: Moon },
    { value: 'auto', label: 'Match system theme', Icon: Monitor },
  ];

  return (
    <ToggleGroup.Root type="single" value={choice} onValueChange={select} aria-label="Color theme" className="theme-toggle">
      {items.map(({ value, label, Icon }) => (
        <ToggleGroup.Item key={value} value={value} aria-label={label} title={label} className="theme-toggle__item">
          <Icon size={16} strokeWidth={1.5} aria-hidden="true" />
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
