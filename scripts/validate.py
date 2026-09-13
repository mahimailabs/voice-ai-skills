#!/usr/bin/env python3
"""Validate the skills in this repository.

No third-party dependencies. Checks structure, frontmatter, size, headings and
all Markdown links. Each skill must work when copied without its siblings. Exits 1 on the first failure set.

Usage:
    python scripts/validate.py [--skills-dir skills]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESC_MIN = 1
DESC_MAX = 1024
MAX_LINES = 500

REQUIRED_HEADINGS = ["## Use this when", "## Do not", "## Adapters"]
NO_ADAPTERS = {"voice-agent-review"}

# Markdown links: [text](target). Skips images, anchors, mailto and http(s).
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


class Failure(Exception):
    pass


def parse_frontmatter(text: str, path: str) -> dict:
    """Parse the YAML frontmatter block. Supports scalars and one nested map."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise Failure(f"{path}: missing '---' on line 1 (no YAML frontmatter)")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise Failure(f"{path}: frontmatter is not closed with '---'")

    data: dict = {}
    parent: str | None = None
    for number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indented = raw.startswith((" ", "\t"))
        if ":" not in raw:
            raise Failure(f"{path}:{number}: frontmatter line is not 'key: value'")
        key, _, value = raw.partition(":")
        key = key.strip()
        if (indented and parent and key in data[parent]) or (not indented and key in data):
            raise Failure(f"{path}:{number}: duplicate frontmatter key '{key}'")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        elif ": " in value or " #" in value:
            raise Failure(
                f"{path}:{number}: unquoted value contains ': ' or ' #', which strict YAML "
                f"parsers reject. Rephrase it or quote the whole value."
            )
        if indented:
            if parent is None:
                raise Failure(f"{path}:{number}: indented key '{key}' has no parent")
            data[parent][key] = value
        elif value == "":
            parent = key
            data[key] = {}
        else:
            parent = None
            data[key] = value
    return data


def check_links(text: str, skill_dir: str, path: str, failures: list) -> None:
    root = Path(skill_dir).resolve()
    for target in LINK_RE.findall(text):
        if target.startswith("#") or urlsplit(target).scheme:
            continue
        target = unquote(urlsplit(target).path)
        if not target:
            continue
        resolved = (Path(path).parent / target).resolve()
        if not resolved.is_relative_to(root):
            failures.append(f"{path}: link escapes the installable skill: {target}")
        elif not resolved.exists():
            failures.append(f"{path}: relative link does not resolve: {target}")


def check_skill(skill_dir: str, failures: list) -> None:
    folder = os.path.basename(skill_dir)
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(path):
        failures.append(f"{folder}: no SKILL.md in {skill_dir}")
        return

    with open(path, encoding="utf-8") as handle:
        text = handle.read()

    try:
        front = parse_frontmatter(text, path)
    except Failure as error:
        failures.append(str(error))
        return

    name = front.get("name")
    if not isinstance(name, str) or not name:
        failures.append(f"{path}: frontmatter has no 'name'")
    else:
        if name != folder:
            failures.append(f"{path}: name '{name}' does not match folder '{folder}'")
        if not NAME_RE.match(name):
            failures.append(f"{path}: name '{name}' must match ^[a-z0-9]+(-[a-z0-9]+)*$")
        if len(name) > NAME_MAX:
            failures.append(f"{path}: name is {len(name)} chars, max is {NAME_MAX}")

    description = front.get("description")
    if not isinstance(description, str) or len(description) < DESC_MIN:
        failures.append(f"{path}: frontmatter needs a 'description' of at least {DESC_MIN} char")
    elif len(description) > DESC_MAX:
        failures.append(f"{path}: description is {len(description)} chars, max is {DESC_MAX}")

    compatibility = front.get("compatibility")
    if compatibility is not None and (not isinstance(compatibility, str) or not 1 <= len(compatibility) <= 500):
        failures.append(f"{path}: compatibility must be a string of 1 to 500 characters")

    line_count = len(text.split("\n"))
    if line_count > MAX_LINES:
        failures.append(f"{path}: {line_count} lines, max is {MAX_LINES}")

    headings = REQUIRED_HEADINGS if folder not in NO_ADAPTERS else REQUIRED_HEADINGS[:-1]
    for heading in headings:
        if not re.search(rf"^{re.escape(heading)}\s*$", text, re.MULTILINE):
            failures.append(f"{path}: missing required heading '{heading}'")

    # References are executable instructions too; validate the entire installed folder.
    for markdown in Path(skill_dir).rglob("*.md"):
        check_links(markdown.read_text(encoding="utf-8"), skill_dir, str(markdown), failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the skills in this repository.")
    parser.add_argument("--skills-dir", default="skills", help="directory holding skill folders")
    args = parser.parse_args()

    root = os.path.abspath(args.skills_dir)
    if not os.path.isdir(root):
        print(f"FAIL: no skills directory at {root}", file=sys.stderr)
        return 1

    skill_dirs = sorted(
        os.path.join(root, entry)
        for entry in os.listdir(root)
        if os.path.isdir(os.path.join(root, entry)) and not entry.startswith(".")
    )
    if not skill_dirs:
        print(f"FAIL: no skill folders found in {root}", file=sys.stderr)
        return 1

    failures: list = []
    for skill_dir in skill_dirs:
        check_skill(skill_dir, failures)

    if failures:
        print(f"FAIL: {len(failures)} problem(s) in {len(skill_dirs)} skill(s)", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"OK: {len(skill_dirs)} skills validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
