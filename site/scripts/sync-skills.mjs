// Generate the site's pages from the repository itself, so the site can never disagree
// with the skills. Runs before every dev server and build. Generated files are gitignored.
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ROOT = resolve(SITE, '..');
const DOCS = join(SITE, 'src/content/docs');
const REPO = 'https://github.com/mahimailabs/voice-ai-skills';
const BLOB = `${REPO}/blob/main`;
const EDIT = `${REPO}/edit/main`;

// The review skill is the entry point, so it leads; the rest follow the README's order.
const ORDER = ['voice-agent-review', 'voice-pipeline-choice', 'voice-turn-taking', 'voice-interruptions', 'voice-latency-budget',
  'voice-prompting', 'voice-function-tools', 'voice-telephony', 'voice-agent-evals', 'voice-full-duplex'];

const yamlString = (s) => JSON.stringify(s);
const frontmatter = (fields) => `---\n${Object.entries(fields).map(([k, v]) => `${k}: ${v}`).join('\n')}\n---\n\n`;

const parseSkill = (name) => {
  const text = readFileSync(join(ROOT, 'skills', name, 'SKILL.md'), 'utf8');
  const m = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) throw new Error(`${name}: no frontmatter`);
  const description = (m[1].match(/^description:\s*(.*)$/m) ?? [])[1]?.trim() ?? '';
  let body = m[2].replace(/^\s*\n/, '');
  const h1 = body.match(/^# (.+)\n/);
  if (!h1) throw new Error(`${name}: no H1`);
  body = body.slice(h1[0].length);
  return { name, title: h1[1].trim(), description, body };
};

// Links inside a skill point at files next to it (references/, scripts/) or at sibling skills
// on GitHub. Siblings become site pages; everything else becomes a GitHub link.
const rewriteLinks = (md, baseDir) =>
  md.replace(/(?<!!)\[([^\]]*)\]\(([^)\s]+)\)/g, (all, text, target) => {
    const sibling = target.match(/^https:\/\/github\.com\/mahimailabs\/voice-ai-skills\/blob\/main\/skills\/([a-z0-9-]+)\/SKILL\.md(#.*)?$/);
    if (sibling) return `[${text}](/skills/${sibling[1]}/${sibling[2] ?? ''})`;
    if (/^(https?:|mailto:|#)/.test(target)) return all;
    const [path, hash = ''] = target.split('#');
    const resolved = join(baseDir, path).replace(/\\/g, '/');
    if (resolved === 'docs/neutrality.md') return `[${text}](/neutrality/${hash ? '#' + hash : ''})`;
    const skillPage = resolved.match(/^skills\/([a-z0-9-]+)\/SKILL\.md$/);
    if (skillPage) return `[${text}](/skills/${skillPage[1]}/${hash ? '#' + hash : ''})`;
    return `[${text}](${BLOB}/${resolved}${hash ? '#' + hash : ''})`;
  });

const section = (body, heading) => {
  const start = body.indexOf(`\n${heading}\n`);
  if (start < 0) return '';
  const rest = body.slice(start + heading.length + 2);
  const end = rest.search(/\n## /);
  return (end < 0 ? rest : rest.slice(0, end)).trim();
};

// ------------------------------------------------------------------ skills
const found = readdirSync(join(ROOT, 'skills')).filter((d) => existsSync(join(ROOT, 'skills', d, 'SKILL.md')));
const missing = found.filter((d) => !ORDER.includes(d));
if (missing.length) throw new Error(`add to ORDER in sync-skills.mjs: ${missing.join(', ')}`);
const skills = ORDER.filter((n) => found.includes(n)).map(parseSkill);

rmSync(join(DOCS, 'skills'), { recursive: true, force: true });
mkdirSync(join(DOCS, 'skills'), { recursive: true });
skills.forEach((s, i) => {
  const intro = `:::note[Source]\nThis page is [\`skills/${s.name}/SKILL.md\`](${BLOB}/skills/${s.name}/SKILL.md), rendered as is. Install it with \`npx skills add mahimailabs/voice-ai-skills --skill ${s.name}\`.\n:::\n\n`;
  writeFileSync(join(DOCS, 'skills', `${s.name}.md`),
    frontmatter({ title: yamlString(s.title), description: yamlString(s.description), editUrl: yamlString(`${EDIT}/skills/${s.name}/SKILL.md`), sidebar: `\n  order: ${i}` }) +
    intro + rewriteLinks(s.body, `skills/${s.name}`));
});

// ------------------------------------------------------------------ every "Do not", on one page
const doNots = skills.map((s) => {
  const list = section(s.body, '## Do not');
  return list ? `## ${s.title}\n\n${rewriteLinks(list, `skills/${s.name}`)}\n\n[Read ${s.title} →](/skills/${s.name}/)\n` : '';
}).filter(Boolean).join('\n');
writeFileSync(join(DOCS, 'do-not.md'),
  frontmatter({ title: yamlString('Every “Do not”'), description: yamlString('The mistakes a coding agent is likely to make when it builds a voice agent, from every skill in one place.') }) +
  `Each skill opens with a **Do not** list: the places where a coding agent's default behavior is wrong for voice. They are collected here, one section per skill, each followed by a link to the full skill.\n\n` + doNots);

// ------------------------------------------------------------------ neutrality policy
const neutral = readFileSync(join(ROOT, 'docs/neutrality.md'), 'utf8').replace(/^# .+\n+/, '');
writeFileSync(join(DOCS, 'neutrality.md'),
  frontmatter({ title: yamlString('Vendor neutrality and adapter policy'), description: yamlString('The rules that keep the collection vendor-neutral, for contributors and for vendors.'), editUrl: yamlString(`${EDIT}/docs/neutrality.md`) }) +
  rewriteLinks(neutral, 'docs'));

// ------------------------------------------------------------------ home, from the README
const readme = readFileSync(join(ROOT, 'README.md'), 'utf8');
const table = section(readme, '## The skills').replace(/\]\(skills\/([a-z0-9-]+)\/\)/g, '](/skills/$1/)');
const tryIt = section(readme, '## Try it');
const install = readFileSync(join(SITE, 'src/data/install-output.txt'), 'utf8').trimEnd();
writeFileSync(join(DOCS, 'index.mdx'),
  frontmatter({
    title: yamlString('Voice AI Skills'),
    description: yamlString('Vendor-neutral engineering judgment for the coding agent building your voice agent. Ten skills, versioned adapters for LiveKit, Pipecat, and Vapi.'),
    template: 'splash',
    hero: `\n  title: ${yamlString('Engineering judgment for the coding agent building your voice agent.')}\n  tagline: ${yamlString('A pause is not always the end of a turn. A cough should not cancel a reply. A booking needs a read-back and a clear yes before the write. Ten skills teach your coding agent those decisions.')}\n  actions:\n    - text: Start with the review\n      link: /skills/voice-agent-review/\n      icon: right-arrow\n    - text: View on GitHub\n      link: ${REPO}\n      icon: external\n      variant: minimal`,
  }) +
  `## Install\n\nInstall the review skill into your project. This is the installer's real output, captured on a fresh project:\n\n\`\`\`text title="Terminal"\n${install}\n\`\`\`\n\n` +
  `Install every skill with \`npx skills add mahimailabs/voice-ai-skills --skill '*'\`. The installer needs Node.js 22.20 or later; see [manual installation](${REPO}#install) otherwise.\n\n` +
  `## Try it\n\n${tryIt}\n\n## The skills\n\n${table}\n\n` +
  `## Vendor-neutral by rule\n\nThe core of every skill never recommends a provider. Adapters for LiveKit, Pipecat, and Vapi are pinned to a version and a verification date, and every stack gets the same fields. The rules are in the [neutrality policy](/neutrality/).\n`);

console.log(`sync-skills: ${skills.length} skills, do-not, neutrality, home`);
