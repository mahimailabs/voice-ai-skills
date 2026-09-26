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
rmSync(join(DOCS, 'index.mdx'), { force: true }); // the home page is src/pages/index.astro
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

// ------------------------------------------------------------------ home data, from the README and the skills
// src/pages/index.astro renders this. Nothing on the home page is typed twice.
const readme = readFileSync(join(ROOT, 'README.md'), 'utf8');
const cells = (row) => row.split('|').slice(1, -1).map((c) => c.trim());
const rows = section(readme, '## The skills').split('\n').filter((l) => /^\| \[voice-/.test(l)).map(cells);
const skillRows = rows.map(([link, decides, useWhen]) => {
  const name = link.match(/\[([a-z0-9-]+)\]/)[1];
  return { name, title: skills.find((s) => s.name === name)?.title ?? name, decides, useWhen };
});
const prompts = [...section(readme, '## Try it').matchAll(/^> (.+(?:\n> .+)*)/gm)].map((m) => m[1].replace(/\n> /g, ' '));
// the adapter header of one skill, verbatim: what "pinned to a version and a date" looks like
const adapters = readFileSync(join(ROOT, 'skills/voice-interruptions/references/adapters.md'), 'utf8');
const stamps = ['LiveKit Agents', 'Pipecat', 'Vapi'].map((stack) => {
  const after = adapters.split(`\n## ${stack}\n`)[1] ?? '';
  const line = after.split('\n').find((l) => l.trim()) ?? '';
  return { stack, pin: line.split(/(?<=\.)\s/)[0] };
});
const transcript = readFileSync(join(SITE, 'src/data/install-output.txt'), 'utf8').trimEnd();
writeFileSync(join(SITE, 'src/data/home.generated.json'), JSON.stringify({ skills: skillRows, prompts, stamps, transcript,
  stampsSource: `${BLOB}/skills/voice-interruptions/references/adapters.md` }, null, 2));

// ------------------------------------------------------------------ the full example review, when one is committed
const reviewPath = join(SITE, 'src/data/clinic-review.md');
if (existsSync(reviewPath)) {
  const review = readFileSync(reviewPath, 'utf8').replace(/^# .+\n+/, '');
  writeFileSync(join(DOCS, 'example-review.md'),
    frontmatter({ title: yamlString('Example review: the clinic agent'), description: yamlString('A real voice-agent-review run on the bundled clinic booking agent, unedited.'), editUrl: 'false' }) +
    `:::note[Real output]\nThis is an unedited \`voice-agent-review\` run against [\`examples/clinic-agent/\`](${BLOB}/examples/clinic-agent/). The example leaves out telephony, durable storage, and an eval suite on purpose, and the score says so.\n:::\n\n` +
    rewriteLinks(review, 'examples/clinic-agent'));
}

console.log(`sync-skills: ${skills.length} skills, do-not, neutrality, home data${existsSync(reviewPath) ? ', example review' : ''}`);
