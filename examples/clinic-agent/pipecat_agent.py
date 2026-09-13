"""Clinic appointment booking agent on Pipecat 1.10.

Run: uv run --with "pipecat-ai[daily,deepgram,cartesia,openai,silero]==1.10.0" \
        --with python-dotenv pipecat_agent.py
Same agent as livekit_agent.py, same rules from skills/. README.md maps code to skill.
Verified against pipecat-ai 1.10.0 on 13 September 2026. Re-check before you ship.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat_metrics import VoiceMetricsObserver
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.turns.user_start import MinWordsUserTurnStartStrategy
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

load_dotenv()
logger = logging.getLogger("clinic-agent")

from clinic import BookingError, Clinic, INSTRUCTIONS, StepLimitError
from pipecat.frames.frames import FunctionCallResultProperties, InputAudioRawFrame, LLMContextFrame, TTSSpeakFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.turns.user_mute import BaseUserMuteStrategy


class ReadbackMute(BaseUserMuteStrategy):
    def __init__(self):
        super().__init__()
        self.muted = False

    async def process_frame(self, frame):
        await super().process_frame(frame)
        return self.muted


class ReadbackInputGate(FrameProcessor):
    """Drop microphone audio before STT while the exact read-back plays."""
    def __init__(self, mute):
        super().__init__()
        self.mute = mute

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if self.mute.muted and isinstance(frame, InputAudioRawFrame):
            return
        await self.push_frame(frame, direction)


class UserTurnGate(FrameProcessor):
    """Update authorization before the finalized context can reach the LLM.

    This demo keeps full context. A summarizing app needs stable turn IDs instead.
    """
    def __init__(self, clinic):
        super().__init__()
        self.clinic = clinic
        self.user_count = 0

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMContextFrame) and direction == FrameDirection.DOWNSTREAM:
            users = [m for m in frame.context.messages if isinstance(m, dict) and m.get("role") == "user"]
            if len(users) != self.user_count:
                self.user_count = len(users)
                text = users[-1].get("content", "") if users else ""
                self.clinic.user_turn(text if isinstance(text, str) else "")
        await self.push_frame(frame, direction)


class ClinicTools:
    def __init__(self):
        self.clinic = Clinic()
        self.mute = ReadbackMute()
        self.receipt = None
        self.expected = ""

    @staticmethod
    def words(text):
        import re
        return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))

    async def on_spoken(self, aggregator, message):
        # A different utterance or a partial/interrupted read-back is no receipt.
        if self.receipt and not self.receipt.done() and not message.interrupted:
            if self.words(message.content or "").endswith(self.words(self.expected)):
                self.receipt.set_result(None)

    async def speak(self, params, text, protected):
        if not protected:
            await params.llm.push_frame(TTSSpeakFrame(text))
            return
        self.mute.muted = True
        self.expected = text
        self.receipt = asyncio.get_running_loop().create_future()
        try:
            await params.llm.push_frame(TTSSpeakFrame(text))
            await asyncio.wait_for(self.receipt, 30)
        except asyncio.TimeoutError:
            raise BookingError("I could not finish the read-back. Please contact the front desk.") from None
        finally:
            self.mute.muted = False
            self.receipt = None
            self.expected = ""

    async def invoke(self, params, method, *args, spoken=False):
        async def speak(text, protected):
            await self.speak(params, text, protected)
        try:
            result = await method(*args, speak)
        except StepLimitError as error:
            await self.speak(params, str(error), False)
            await params.result_callback({"status": "tool limit; wait for caller"},
                                        properties=FunctionCallResultProperties(run_llm=False))
        except BookingError as error:
            await params.result_callback({"say": str(error)})
        except Exception:
            await params.result_callback({"say": "The request could not be confirmed. Please contact the front desk before trying again."})
        else:
            await params.result_callback(result or {"status": "spoken; wait for caller"},
                                        properties=FunctionCallResultProperties(run_llm=not spoken))

    async def lookup_patient(self, params: FunctionCallParams, full_name: str, date_of_birth: str):
        """Find the caller after reading back their date of birth.

        Args:
            full_name: The caller's full name.
            date_of_birth: Confirmed date in YYYY-MM-DD format.
        """
        await self.invoke(params, self.clinic.lookup, full_name, date_of_birth)

    async def check_availability(self, params: FunctionCallParams, physician: str,
                                 date_range: str, appointment_type: str):
        """Find up to three times; keep the silent slot IDs for booking.

        Args:
            physician: Requested physician, or any.
            date_range: Requested date window.
            appointment_type: routine, follow up, or urgent.
        """
        await self.invoke(params, self.clinic.availability, physician, date_range, appointment_type)

    # Backend deadline is five seconds. The outer deadline also allows protected
    # speech (30 seconds) and one read-only reconciliation (five seconds).
    @tool_options(timeout_secs=45)
    async def book_appointment(self, params: FunctionCallParams, patient_id: str,
                               slot_id: str, appointment_type: str):
        """First call speaks the proposal without writing. Call again only after a new yes.

        Args:
            patient_id: silent_patient_id from lookup_patient.
            slot_id: silent_slot_id of the caller's chosen time.
            appointment_type: The appointment type used in check_availability.
        """
        await self.invoke(params, self.clinic.book, patient_id, slot_id, appointment_type, spoken=True)


async def main() -> None:
    transport = DailyTransport(
        os.getenv("DAILY_ROOM_URL", ""), os.getenv("DAILY_TOKEN"), "Clinic",
        DailyParams(audio_in_enabled=True, audio_out_enabled=True))
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        settings=CartesiaTTSService.Settings(voice=os.getenv("CARTESIA_VOICE_ID")))
    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        # voice-prompting: the system prompt is a service setting, not a chat message.
        settings=OpenAILLMService.Settings(system_instruction=INSTRUCTIONS),
    )

    tools = ClinicTools()
    context = LLMContext(tools=[tools.lookup_patient, tools.check_availability, tools.book_appointment])
    aggregators = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            # voice-turn-taking: VAD is the speech gate, the turn model is the decision.
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            user_turn_strategies=UserTurnStrategies(
                # voice-interruptions: two words, so mm-hm on a phone line is not a stop.
                # Passing start replaces the default start strategies, not adds to them.
                start=[MinWordsUserTurnStartStrategy(min_words=2)],
                stop=[TurnAnalyzerUserTurnStopStrategy(
                    turn_analyzer=LocalSmartTurnAnalyzerV3())],
            ),
            # Mute only the exact read-back and confirmation, not slow reads/filler.
            user_mute_strategies=[tools.mute],
        ),
    )

    aggregators.assistant().add_event_handler("on_assistant_turn_stopped", tools.on_spoken)

    pipeline = Pipeline([
        transport.input(), ReadbackInputGate(tools.mute), stt, aggregators.user(),
        UserTurnGate(tools.clinic), llm, tts,
        transport.output(), aggregators.assistant(),
    ])

    agent = PipelineWorker(
        pipeline,
        name="clinic",
        # voice-latency-budget: TTFB per service, not one number for the call.
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[VoiceMetricsObserver(llm.name, tts.name)],
    )
    runner = WorkerRunner()
    await runner.add_workers(agent)
    await runner.run()


if __name__ == "__main__":
    import sys
    from loguru import logger as framework_logger
    framework_logger.remove()
    framework_logger.add(sys.stderr, level="INFO")
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
