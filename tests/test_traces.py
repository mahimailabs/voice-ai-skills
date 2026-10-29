"""Offline checks for the native trace parsers, using synthetic records."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import traces

SKILLS = {'voice-turn-taking', 'voice-latency-budget'}


def jsonl(*events):
    return '\n'.join(json.dumps(event) for event in events)


def call(id_, name, **given):
    return {'type': 'assistant', 'message': {'content': [
        {'type': 'tool_use', 'id': id_, 'name': name, 'input': given}]}}


def result(id_, content, error=False):
    return {'type': 'user', 'message': {'content': [
        {'type': 'tool_result', 'tool_use_id': id_, 'content': content, 'is_error': error}]}}


class ClaudeTraceTests(unittest.TestCase):
    def test_skill_tool_with_a_result_counts(self):
        raw = jsonl(call('a', 'Skill', skill='voice-turn-taking'),
                    result('a', [{'type': 'text', 'text': 'Launching skill'}]),
                    {'type': 'result', 'result': 'Skill used: voice-turn-taking'})
        parsed = traces.parse_claude(raw, SKILLS)
        self.assertEqual(parsed['loaded'], ['voice-turn-taking'])
        self.assertEqual(parsed['answer'], 'Skill used: voice-turn-taking')

    def test_plugin_namespaced_skill_and_read_of_skill_file_count(self):
        raw = jsonl(call('a', 'Skill', skill='voice-ai:voice-turn-taking'), result('a', 'ok'),
                    call('b', 'Read', file_path='/p/.claude/skills/voice-latency-budget/SKILL.md'),
                    result('b', '# Voice Latency Budget'))
        self.assertEqual(traces.parse_claude(raw, SKILLS)['loaded'], sorted(SKILLS))

    def test_a_mention_is_not_a_load(self):
        raw = jsonl({'type': 'result', 'result': 'I used voice-turn-taking.'})
        self.assertEqual(traces.parse_claude(raw, SKILLS)['loaded'], [])

    def test_a_call_without_a_good_result_is_not_a_load(self):
        raw = jsonl(call('a', 'Skill', skill='voice-turn-taking'),
                    call('b', 'Read', file_path='skills/voice-latency-budget/SKILL.md'),
                    result('b', 'Permission denied', error=True))
        self.assertEqual(traces.parse_claude(raw, SKILLS)['loaded'], [])

    def test_an_empty_result_is_not_a_load(self):
        raw = jsonl(call('a', 'Read', file_path='skills/voice-turn-taking/SKILL.md'), result('a', '  '))
        self.assertEqual(traces.parse_claude(raw, SKILLS)['loaded'], [])

    def test_unicode_line_separators_inside_strings_do_not_split_events(self):
        raw = jsonl(call('a', 'Skill', skill='voice-turn-taking'), result('a', 'one two'))
        self.assertEqual(traces.parse_claude(raw, SKILLS)['loaded'], ['voice-turn-taking'])


class CodexTraceTests(unittest.TestCase):
    def item(self, **item):
        return {'type': 'item.completed', 'item': item}

    def test_a_successful_read_of_the_skill_file_counts(self):
        raw = jsonl(self.item(type='command_execution', exit_code=0,
                              command="sed -n '1,200p' .agents/skills/voice-turn-taking/SKILL.md",
                              aggregated_output='---\nname: voice-turn-taking'),
                    self.item(type='agent_message', text='Skill: voice-turn-taking'))
        parsed = traces.parse_codex(raw, SKILLS)
        self.assertEqual(parsed['loaded'], ['voice-turn-taking'])
        self.assertEqual(parsed['answer'], 'Skill: voice-turn-taking')

    def test_a_failed_or_empty_read_does_not_count(self):
        raw = jsonl(self.item(type='command_execution', exit_code=1,
                              command='cat skills/voice-turn-taking/SKILL.md', aggregated_output='No such file'),
                    self.item(type='command_execution', exit_code=0,
                              command='cat skills/voice-latency-budget/SKILL.md', aggregated_output=''))
        self.assertEqual(traces.parse_codex(raw, SKILLS)['loaded'], [])


if __name__ == '__main__':
    unittest.main()
