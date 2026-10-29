"""Offline checks for the adapter drift report. No network."""
import datetime as dt
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('drift', ROOT / 'scripts/adapter_drift.py')
drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drift)

RELEASES = {'livekit-agents': ['1.7.9', '1.8.0', '1.8.1', '1.8.2', '1.9.0', '2.0.0']}


def adapter(pinned='1.8', verified='2026-09-11'):
    return {'skill': 'voice-turn-taking', 'stack': 'LiveKit Agents', 'package': 'livekit-agents',
            'pinned': pinned, 'verified': verified}


class DriftTests(unittest.TestCase):
    def test_series_pin_ignores_patches_inside_the_series(self):
        self.assertEqual(drift.behind('1.8', RELEASES['livekit-agents']), (2, 2))
        self.assertEqual(drift.behind('1.8', ['1.8.0', '1.8.5']), (0, 0))

    def test_exact_pin_counts_every_newer_release(self):
        self.assertEqual(drift.behind('1.8.1', RELEASES['livekit-agents']), (3, 2))

    def test_new_minor_release_makes_an_adapter_due(self):
        row = adapter()
        drift.assess([row], [], RELEASES, dt.date(2026, 9, 20))
        self.assertEqual(row['status'], 'due')

    def test_age_alone_makes_an_adapter_due_then_stale(self):
        row = adapter(pinned='unversioned')
        drift.assess([row], [], RELEASES, dt.date(2026, 9, 20))
        self.assertEqual(row['status'], 'ok')
        drift.assess([row], [], RELEASES, dt.date(2026, 12, 20))
        self.assertEqual(row['status'], 'due')
        drift.assess([row], [], RELEASES, dt.date(2027, 3, 20))
        self.assertEqual(row['status'], 'stale')

    def test_every_shipped_adapter_has_a_stamp(self):
        adapters, pins = drift.collect()
        self.assertTrue(adapters)
        self.assertIn('livekit-agents', {p['package'] for p in pins})

    def test_report_renders_rows(self):
        row = adapter()
        drift.assess([row], [], RELEASES, dt.date(2026, 9, 20))
        text = drift.report([row], [], dt.date(2026, 9, 20))
        self.assertIn('| voice-turn-taking | LiveKit Agents | 1.8 | 2.0.0 | 2 |', text)
        self.assertIn('1 of 1 adapters need a refresh.', text)


class StampTests(unittest.TestCase):
    def check(self, text):
        failures = []
        drift.validator.adapter_stamps(text, 'SKILL.md', failures)
        return failures

    def test_missing_stamp_fails(self):
        self.assertTrue(self.check('## Adapters\n\n### Vapi\n\nUnversioned docs, checked 1 May 2026.\n'))

    def test_stamp_date_must_match_the_prose(self):
        text = ('## Adapters\n\n### Vapi\n\n<!-- adapter: package=none pinned=unversioned '
                'verified=2026-05-01 -->\nUnversioned docs, checked {} 2026.\n')
        self.assertEqual(self.check(text.format('1 May')), [])
        self.assertTrue(self.check(text.format('2 May')))


if __name__ == '__main__':
    unittest.main()
