# Coding-agent compatibility

The installable product is ten self-contained folders in the open
[Agent Skills format](https://agentskills.io/specification). It does not require a
Claude or Codex runtime. A client must discover the metadata, load `SKILL.md`, and
follow relative references; running the optional helper also requires shell access
and Python 3.10+. SDK verification needs official documentation access or supplied
version-matched documentation. No particular MCP server is mandatory.

## Evidence as of September 13, 2026

| Client target | Documented project location | Local installer checks | Native model acceptance |
| --- | --- | --- | --- |
| [Claude Code](https://code.claude.com/docs/en/skills) | `.claude/skills/` | Copy and symlink; bundle and all ten selective installs | Not run |
| [Codex](https://learn.chatgpt.com/docs/build-skills) | `.agents/skills/` | Same | Not run |
| [Cursor](https://cursor.com/docs/skills) | `.agents/skills/` | Same | Not run |
| [Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/) | `.agents/skills/` | Same | Not run |
| [GitHub Copilot](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) | `.agents/skills/` | Same | Not run |
| Other clients | Check their documented discovery/import mechanism | Not run | Not run |

Checks use [`skills@1.5.26`](https://github.com/vercel-labs/skills) against the working
checkout in disposable project directories. They validate file contents, local links,
and calculator execution after installation. Four targets share the canonical
`.agents/skills/` tree; these are not four independent model sessions. Claude's
marketplace manifest also validates, but marketplace installation and authenticated
model sessions are separate from the local installer test.

**This is installation evidence, not a promise that every coding agent follows every
rule.** Use the [native acceptance cases](../tests/agents/cases.json) and
[test procedure](testing.md) before calling another client behavior-tested. Remote
installation from GitHub sees published commits, not uncommitted local changes.

## Selective and offline use

Local references and helpers stay inside each skill directory. Links to other skills
are optional repository URLs. Look for an installed skill by name first; when one is
missing, use the current skill's rules and explicitly name unavailable deeper analysis.
The review skill includes its own 40-item checklist and can produce a bounded review
without downloading siblings.

If current vendor docs cannot be reached, continue the vendor-neutral review. Use
supplied version-matched docs where available, label unverified API details, and do
not invent a method signature or claim an integration was tested. With no shell or
Python, use the latency skill's tables and arithmetic instead of claiming the helper ran.
