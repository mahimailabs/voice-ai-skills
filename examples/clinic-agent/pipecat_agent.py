"""Clinic appointment booking agent on Pipecat 1.10.

Run: uv run --with "pipecat-ai[daily,deepgram,cartesia,openai,silero]~=1.10" \
        --with python-dotenv pipecat_agent.py
Same agent as livekit_agent.py, same rules from skills/. README.md maps line to skill.
Verified against pipecat-ai 1.10.0 on 11 September 2026. Re-check before you ship.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver
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
from pipecat.turns.user_mute import FunctionCallUserMuteStrategy
from pipecat.turns.user_start import MinWordsUserTurnStartStrategy
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies
from pipecat.workers.runner import WorkerRunner

load_dotenv()
logger = logging.getLogger("clinic-agent")

TOOL_TIMEOUT = 5.0  # voice-function-tools: every tool call has a deadline

# voice-prompting: spoken output, then persona, then task, then confirmation.
INSTRUCTIONS = """\
You are the scheduling line for Riverside Family Medicine.
How you speak. You are heard, not read. No markdown, no lists, no asterisks, no emoji.
One idea per sentence, under twenty words. Say the fourteenth, not 14. Say a time as
three fifteen in the afternoon, and a phone number as five five five, zero one two three.
Who you are. Calm and brief. You are not a clinician. No medical advice and no triage.
If a caller describes an emergency, tell them to hang up and call emergency services.
What you do. Book, reschedule and cancel appointments, and nothing else. Take the full
name and date of birth first. Offer at most three times. Never invent one.
How you confirm. Read the booking back in full before you book it: patient, day, date,
time and physician. Wait for a clear yes, then call book_appointment. Say the
confirmation number exactly as book_appointment returns it, word for word.
"""


async def lookup_patient(params: FunctionCallParams, full_name: str, date_of_birth: str):
    """Find the record for a caller who has given a name and date of birth.

    Args:
        full_name: The caller's full name, exactly as they said it.
        date_of_birth: The caller's date of birth, as day, month and year.
    """
    logger.info("lookup_patient called")  # the framework logs arguments at DEBUG: run at INFO
    patient = await asyncio.wait_for(_find_patient(full_name, date_of_birth), TOOL_TIMEOUT)
    if patient is None:
        await params.result_callback({"error": "No record matched. Ask them to repeat the date."})
        return
    await params.result_callback({"patient_id": patient["id"], "physician": patient["physician"]})


async def check_availability(
    params: FunctionCallParams, physician: str, date_range: str, appointment_type: str
):
    """Find open appointment times. Read only, so it is safe to call again.

    Args:
        physician: The physician the caller asked for, or "any".
        date_range: The window the caller asked for, such as "next week".
        appointment_type: One of "routine", "follow up" or "urgent".
    """
    slots = await asyncio.wait_for(_availability(physician, date_range, appointment_type), 5.0)
    # voice-function-tools: a sentence to say, not raw rows to read aloud.
    spoken = "; ".join(x["spoken"] for x in slots[:3]) or "nothing in that window"
    await params.result_callback({"say": f"Open times: {spoken}"})


# voice-function-tools: a deadline on the write. It stays synchronous, because
# cancel_on_interruption=False would make it async and the code would miss this turn.
@tool_options(timeout_secs=TOOL_TIMEOUT)
async def book_appointment(
    params: FunctionCallParams, patient_id: str, slot_id: str, appointment_type: str
):
    """Book a slot the caller has already confirmed out loud. This writes.

    Args:
        patient_id: The id returned by lookup_patient.
        slot_id: The id of the slot the caller confirmed.
        appointment_type: One of "routine", "follow up" or "urgent".
    """
    booking = await _book(patient_id, slot_id, appointment_type)
    await params.result_callback({
        "say": f"You are booked for {booking['when']} with Doctor {booking['physician']}. "
               f"Your confirmation number is {booking['code']}."})


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

    context = LLMContext(tools=[lookup_patient, check_availability, book_appointment])
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
            # voice-interruptions: this mutes the caller while a tool runs, so the write
            # is not raced. It does NOT protect the read-back sentence before the call.
            # On this stack, muting is the only real gate: disabling interruptions still
            # lets speech over the agent become a turn. See the skill before shipping.
            user_mute_strategies=[FunctionCallUserMuteStrategy()],
        ),
    )

    pipeline = Pipeline([
        transport.input(), stt, aggregators.user(), llm, tts,
        transport.output(), aggregators.assistant(),
    ])

    agent = PipelineWorker(
        pipeline,
        name="clinic",
        # voice-latency-budget: TTFB per service, not one number for the call.
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=[MetricsLogObserver()],
    )
    runner = WorkerRunner()
    await runner.add_workers(agent)
    await runner.run()


# Stand-ins for the clinic scheduling API. Replace with the real client.
async def _find_patient(full_name: str, date_of_birth: str):
    return {"id": "p_4417", "physician": "Osei"}

async def _availability(physician: str, date_range: str, kind: str):
    return [{"id": "s_91", "spoken": "Tuesday the fourteenth at three fifteen"}]

async def _book(patient_id: str, slot_id: str, kind: str):
    return {"when": "Tuesday the fourteenth at three fifteen", "physician": "Osei",
            "code": "four seven two one"}


if __name__ == "__main__":
    asyncio.run(main())
