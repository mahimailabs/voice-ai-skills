"""SDK contract checks using real pinned packages and fake speech/backend I/O."""
import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'examples/clinic-agent'))
import livekit_agent
from clinic import BookingError, StepLimitError
from pipecat_agent import ClinicTools, ReadbackInputGate, UserTurnGate
from pipecat_metrics import VoiceMetricsObserver
from pipecat.frames.frames import (InputAudioRawFrame, LLMContextFrame, TTSSpeakFrame, TranscriptionFrame,
    VADUserStartedSpeakingFrame, VADUserStoppedSpeakingFrame, BotStartedSpeakingFrame, MetricsFrame)
from pipecat.metrics.metrics import TTFBMetricsData
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipecat_microphone_gate_precedes_stt(self):
        tools = ClinicTools()
        gate = ReadbackInputGate(tools.mute)
        gate.push_frame = AsyncMock()
        gate._check_started = lambda frame: True
        frame = InputAudioRawFrame(audio=b'\x00\x00', sample_rate=16000, num_channels=1)
        tools.mute.muted = True
        await gate.process_frame(frame, FrameDirection.DOWNSTREAM)
        gate.push_frame.assert_not_awaited()
        tools.mute.muted = False
        await gate.process_frame(frame, FrameDirection.DOWNSTREAM)
        gate.push_frame.assert_awaited_once()

    async def test_pipecat_playout_receipt_keeps_input_muted(self):
        tools = ClinicTools()
        params = SimpleNamespace(llm=SimpleNamespace(push_frame=AsyncMock()))
        task = asyncio.create_task(tools.speak(params, 'Is that right?', True))
        await asyncio.sleep(0)
        self.assertTrue(tools.mute.muted)
        self.assertIsInstance(params.llm.push_frame.call_args.args[0], TTSSpeakFrame)
        await tools.on_spoken(None, SimpleNamespace(content='Is that right?', interrupted=True))
        self.assertFalse(task.done())
        await tools.on_spoken(None, SimpleNamespace(content='Unrelated speech', interrupted=False))
        self.assertFalse(task.done())
        await tools.on_spoken(None, SimpleNamespace(content='Is that right?', interrupted=False))
        await task
        self.assertFalse(tools.mute.muted)

    async def test_pipecat_cancel_clears_gate(self):
        tools = ClinicTools()
        params = SimpleNamespace(llm=SimpleNamespace(push_frame=AsyncMock()))
        task = asyncio.create_task(tools.speak(params, 'Is that right?', True))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(tools.mute.muted)
        self.assertIsNone(tools.clinic.pending)

    async def test_pipecat_context_gate_precedes_llm_and_ignores_tool_updates(self):
        tools = ClinicTools()
        gate = UserTurnGate(tools.clinic)
        gate.push_frame = AsyncMock()
        # StartFrame setup isn't needed for a pure context-frame contract check.
        gate._check_started = lambda frame: True
        context = LLMContext(messages=[{'role':'user', 'content':'yes'}],
                             tools=[tools.lookup_patient, tools.check_availability, tools.book_appointment])
        await gate.process_frame(LLMContextFrame(context), FrameDirection.DOWNSTREAM)
        self.assertEqual(tools.clinic.turn, 1)
        context.add_message({'role':'tool', 'tool_call_id':'1', 'content':'result'})
        await gate.process_frame(LLMContextFrame(context), FrameDirection.DOWNSTREAM)
        self.assertEqual(tools.clinic.turn, 1)
        context.add_message({'role':'user', 'content':'yes'})
        await gate.process_frame(LLMContextFrame(context), FrameDirection.DOWNSTREAM)
        self.assertEqual(tools.clinic.turn, 2)

    async def test_pipecat_authored_error_and_no_extra_reply_after_speech(self):
        tools = ClinicTools()
        params = SimpleNamespace(result_callback=AsyncMock())
        operation = AsyncMock(side_effect=BookingError('The calendar is not answering.'))
        await tools.invoke(params, operation)
        self.assertEqual(params.result_callback.call_args.args[0]['say'], 'The calendar is not answering.')
        params.result_callback.reset_mock()
        await tools.invoke(params, AsyncMock(return_value=None), spoken=True)
        self.assertFalse(params.result_callback.call_args.kwargs['properties'].run_llm)

    async def test_pipecat_tool_limit_ends_model_loop(self):
        tools = ClinicTools()
        params = SimpleNamespace(result_callback=AsyncMock(), llm=SimpleNamespace(push_frame=AsyncMock()))
        await tools.invoke(params, AsyncMock(side_effect=StepLimitError('Please contact the front desk.')))
        self.assertFalse(params.result_callback.call_args.kwargs['properties'].run_llm)
        params.llm.push_frame.assert_awaited_once()

    async def test_livekit_turn_hook_and_protected_playout(self):
        agent = livekit_agent.ClinicAgent()
        await agent.on_user_turn_completed(None, SimpleNamespace(text_content='yes'))
        self.assertEqual(agent.clinic.turn, 1)
        handle = SimpleNamespace(wait_for_playout=AsyncMock(), interrupted=False, exception=lambda: None)
        session = SimpleNamespace(say=lambda text, **kwargs: handle)
        fake = SimpleNamespace(session=session)
        await livekit_agent.ClinicAgent.speak(fake, 'Is that right?', True)
        handle.wait_for_playout.assert_awaited_once()
        handle.interrupted = True
        with self.assertRaises(BookingError):
            await livekit_agent.ClinicAgent.speak(fake, 'Is that right?', True)

    async def test_pipecat_five_timing_snapshot_and_duplicate_frames(self):
        observer = VoiceMetricsObserver('llm', 'tts')
        async def push(frame, at):
            await observer.on_push_frame(SimpleNamespace(frame=frame, timestamp=int(at*1e9)))
        await push(VADUserStartedSpeakingFrame(), 1)
        await push(VADUserStoppedSpeakingFrame(stop_secs=.2), 2.2)
        await push(TranscriptionFrame(text='not logged',user_id='u',timestamp=''), 2.3)
        with self.assertLogs('clinic-agent') as output:
            await push(LLMContextFrame(LLMContext()), 2.5)
            await push(MetricsFrame(data=[TTFBMetricsData(processor='llm',value=.1),
                                          TTFBMetricsData(processor='tts',value=.2)]), 2.8)
            frame = BotStartedSpeakingFrame()
            await push(frame, 2.9)
            await push(frame, 3.5)
        self.assertAlmostEqual(observer.values['transcription_delay'], .3)
        self.assertAlmostEqual(observer.values['end_of_turn_delay'], .5)
        self.assertAlmostEqual(observer.values['llm_node_ttft'], .1)
        self.assertAlmostEqual(observer.values['tts_node_ttfb'], .2)
        self.assertAlmostEqual(observer.values['e2e_latency'], .9)
        self.assertNotIn('not logged', str(output.output))
