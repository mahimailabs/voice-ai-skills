"""Deterministic booking regressions, not a voice/model evaluation suite."""
import asyncio
import json
import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples/clinic-agent'))
from clinic import BookingError, Clinic, DemoSchedule, log_metrics


class BookingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.backend = DemoSchedule()
        self.backend.book = AsyncMock(wraps=self.backend.book)
        self.clinic = Clinic(self.backend, timeout=.02, filler_delay=.001)
        self.speak = AsyncMock()
        self.clinic.user_turn('Dana Whitfield, March fourth, nineteen eighty')
        self.patient = await self.clinic.lookup('Dana Whitfield', '1980-03-04', self.speak)
        self.slots = await self.clinic.availability('any', 'next week', 'routine', self.speak)
        self.args = (self.patient['silent_patient_id'], self.slots['slots'][0]['silent_slot_id'], 'routine', self.speak)
        self.clinic.user_turn('That time works')

    async def prepare(self):
        await self.clinic.book(*self.args)
        self.backend.book.assert_not_awaited()
        self.assertTrue(self.speak.call_args.args[1])

    async def test_fresh_yes_required_and_duplicate_is_read_only(self):
        await self.prepare()
        with self.assertRaisesRegex(BookingError, 'Wait for the caller'):
            await self.clinic.book(*self.args)
        self.clinic.user_turn("Yes, that's right.")
        await self.clinic.book(*self.args)
        self.clinic.user_turn('Did you book it?')
        await self.clinic.book(*self.args)
        self.backend.book.assert_awaited_once()

    async def test_prior_yes_and_correction_cannot_authorize(self):
        self.clinic.user_turn('yes')
        await self.prepare()
        self.clinic.user_turn('yes but a different time')
        await self.prepare()
        self.backend.book.assert_not_awaited()

    async def test_unfinished_playout_cannot_arm_confirmation(self):
        self.speak.side_effect = BookingError('read-back interrupted')
        with self.assertRaises(BookingError):
            await self.clinic.book(*self.args)
        self.clinic.user_turn('yes')
        self.assertIsNone(self.clinic.pending)
        self.backend.book.assert_not_awaited()

    async def test_yes_during_playout_cannot_authorize(self):
        async def talk(*args):
            self.clinic.user_turn('yes')
        self.speak.side_effect = talk
        await self.clinic.book(*self.args)
        self.assertIsNone(self.clinic.pending)
        self.backend.book.assert_not_awaited()

    async def test_wrong_slot_or_patient_rejected(self):
        for patient, slot in [('wrong', 's_91'), ('p_4417', 'invented')]:
            with self.assertRaises(BookingError):
                await self.clinic.book(patient, slot, 'routine', self.speak)
        self.backend.book.assert_not_awaited()

    async def test_timeout_after_commit_reconciles_without_rewrite(self):
        original = self.backend.book
        async def committed(choice, key):
            result = await original(choice, key)
            await asyncio.sleep(1)
            return result
        self.backend.book = AsyncMock(side_effect=committed)
        await self.prepare()
        self.clinic.user_turn('yes')
        await self.clinic.book(*self.args)
        self.assertTrue(self.clinic.completed)
        self.backend.book.assert_awaited_once()
        self.assertFalse(self.clinic.uncertain)

    async def test_unresolved_timeout_never_retries_write(self):
        self.backend.book = AsyncMock(side_effect=asyncio.TimeoutError)
        await self.prepare()
        self.clinic.user_turn('yes')
        with self.assertRaisesRegex(BookingError, 'cannot confirm whether'):
            await self.clinic.book(*self.args)
        self.clinic.user_turn('try again')
        with self.assertRaisesRegex(BookingError, 'cannot confirm whether'):
            await self.clinic.book(*self.args)
        self.backend.book.assert_awaited_once()

    async def test_all_reads_have_safe_timeout_and_interruptible_filler(self):
        async def slow(*args):
            await asyncio.sleep(1)
        for name, action in [('availability', lambda: self.clinic.availability('any', 'next week', 'routine', self.speak)),
                             ('find_patient', lambda: self.clinic.lookup('Dana Whitfield','1980-03-04',self.speak))]:
            self.clinic.user_turn('try the read')
            setattr(self.backend, name, slow)
            self.speak.reset_mock()
            with self.assertRaisesRegex(BookingError, 'not answering'):
                await action()
            self.speak.assert_awaited_once_with('Let me check that.', False)

    async def test_concurrent_tools_and_turn_limit(self):
        with self.clinic.tool():
            with self.assertRaisesRegex(BookingError, 'already running'):
                await self.clinic.book(*self.args)
        self.clinic.steps = 3
        with self.assertRaisesRegex(BookingError, 'front desk'):
            await self.clinic.book(*self.args)
        self.clinic.user_turn('new request')
        await self.prepare()


class MetricsTests(unittest.TestCase):
    def test_missing_is_null_and_zero_is_preserved(self):
        logger = logging.getLogger('metric-test')
        with self.assertLogs(logger) as logs:
            log_metrics(logger, turn_id='1', role='user', scope='test', metrics={'transcription_delay': 0})
        record = json.loads(logs.output[0].split('voice_metrics ', 1)[1])
        self.assertEqual(record['transcription_delay'], 0)
        self.assertIsNone(record['llm_node_ttft'])
        self.assertEqual(len(record), 8)
