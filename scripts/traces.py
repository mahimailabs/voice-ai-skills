"""Read native coding-agent traces and prove which skills were actually loaded.

A skill counts as loaded only when the trace holds a tool call that opened it and a
matching tool result that is not an error and is not empty. Naming the skill in the
answer is not evidence, and neither is a tool call without its result.

Supported formats:
  claude  Claude Code `-p --output-format stream-json --verbose` (JSON Lines)
  codex   Codex `exec --json` (JSON Lines)
"""
from __future__ import annotations

import json


def _lines(raw: str):
    # Split on LF only: str.splitlines() also breaks on Unicode separators inside JSON strings.
    for line in raw.split('\n'):
        line = line.strip()
        if line.startswith('{'):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return ''.join(part.get('text', '') for part in content
                       if isinstance(part, dict) and isinstance(part.get('text'), str))
    return ''


def _opened(target: str, skills: set[str]) -> set[str]:
    target = target.replace('\\', '/')
    return {name for name in skills
            if target == name or target.endswith(':' + name) or f'{name}/SKILL.md' in target}


def parse_claude(raw: str, skills: set[str]) -> dict:
    calls: dict[str, set[str]] = {}
    loaded: set[str] = set()
    answer = ''
    for event in _lines(raw):
        if event.get('type') == 'result' and isinstance(event.get('result'), str):
            answer = event['result']
        content = event.get('message', {}).get('content', [])
        for block in content if isinstance(content, list) else []:
            if event.get('type') == 'assistant' and block.get('type') == 'tool_use':
                given = block.get('input', {})
                if block.get('name') == 'Skill':
                    calls[block['id']] = _opened(str(given.get('skill', '')), skills)
                elif block.get('name') == 'Read':
                    calls[block['id']] = _opened(str(given.get('file_path', '')), skills)
            if event.get('type') == 'user' and block.get('type') == 'tool_result':
                if not block.get('is_error') and _text(block.get('content')).strip():
                    loaded |= calls.get(block.get('tool_use_id'), set())
    return {'answer': answer, 'loaded': sorted(loaded)}


def parse_codex(raw: str, skills: set[str]) -> dict:
    loaded: set[str] = set()
    answer = ''
    for event in _lines(raw):
        item = event.get('item', {})
        if event.get('type') != 'item.completed':
            continue
        if item.get('type') == 'agent_message':
            answer = item.get('text', answer)
        if (item.get('type') == 'command_execution' and item.get('exit_code') == 0
                and str(item.get('aggregated_output', '')).strip()):
            loaded |= _opened(str(item.get('command', '')), skills)
    return {'answer': answer, 'loaded': sorted(loaded)}


PARSERS = {'claude': parse_claude, 'codex': parse_codex}
