"""Clinic appointment booking agent on LiveKit Agents 1.8.

Run: uv run --with "livekit-agents~=1.8" --with python-dotenv livekit_agent.py dev
Each choice is a rule from skills/. README.md maps line to skill. Verified against
LiveKit Agents 1.8.1 on 11 September 2026. Re-check the API before you ship this.
"""

import asyncio
import logging

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import inference
from livekit.agents.llm import ChatMessage

load_dotenv()
logger = logging.getLogger("clinic-agent")


class _DropPII(logging.Filter):
    """The framework logs tool arguments at DEBUG under lk.pii.* keys. Strip them."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in [k for k in record.__dict__ if k.startswith("lk.pii.")]:
            delattr(record, key)
        return True

TOOL_TIMEOUT = 5.0  # voice-function-tools: every tool call has a deadline
FILLER_DELAY = 1.5  # voice-function-tools: speak before the line goes silent

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
time and physician. Wait for a clear yes, then call book_appointment. Do not say the
confirmation number yourself. The tool says it.
"""


class ClinicAgent(agents.Agent):
    def __init__(self) -> None:
        super().__init__(instructions=INSTRUCTIONS)

    @agents.function_tool()
    async def lookup_patient(
        self, context: agents.RunContext, full_name: str, date_of_birth: str
    ) -> str:
        """Find the record for a caller who has given a name and date of birth.
        Args:
            full_name: The caller's full name, exactly as they said it.
            date_of_birth: The caller's date of birth, as day, month and year.
        """
        logger.info("lookup_patient called")  # arguments never reach the logs, see _DropPII
        try:
            patient = await asyncio.wait_for(_find_patient(full_name, date_of_birth), TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            raise agents.ToolError("The patient system did not answer. Ask the caller to hold.")
        if patient is None:
            raise agents.ToolError("No record matched. Ask them to repeat the date of birth.")
        return f"Patient {patient['id']} is on file with Doctor {patient['physician']}."

    @agents.function_tool()
    async def check_availability(
        self, context: agents.RunContext, physician: str, date_range: str, appointment_type: str
    ) -> str:
        """Find open appointment times. Read only, so it is safe to call again.
        Args:
            physician: The physician the caller asked for, or "any".
            date_range: The window the caller asked for, such as "next week".
            appointment_type: One of "routine", "follow up" or "urgent".
        """
        async with context.with_filler("Let me check that.", delay=FILLER_DELAY):
            try:
                slots = await asyncio.wait_for(
                    _availability(physician, date_range, appointment_type), TOOL_TIMEOUT)
            except asyncio.TimeoutError:
                raise agents.ToolError("The calendar did not answer. Offer to call back.")
        if not slots:
            return "No times are open in that window. Offer the next window."
        return "Open times: " + "; ".join(x["spoken"] for x in slots[:3])

    @agents.function_tool()
    async def book_appointment(
        self, context: agents.RunContext, patient_id: str, slot_id: str, appointment_type: str
    ) -> None:
        """Book a slot the caller has already confirmed out loud. This writes.
        Args:
            patient_id: The id returned by lookup_patient.
            slot_id: The id of the slot the caller confirmed.
            appointment_type: One of "routine", "follow up" or "urgent".
        """
        # voice-interruptions: THE READ-BACK GATE. A confirmation is never cut off.
        context.disallow_interruptions()
        async with context.with_filler("One moment while I book that.", delay=FILLER_DELAY):
            try:
                booking = await asyncio.wait_for(
                    _book(patient_id, slot_id, appointment_type), TOOL_TIMEOUT)
            except asyncio.TimeoutError:
                raise agents.ToolError("Nothing was booked. Say so and offer to call back.")
        # voice-pipeline-choice: a cascade, so the code is said word for word.
        handle = context.session.say(
            f"You are booked for {booking['when']} with Doctor {booking['physician']}. "
            f"Your confirmation number is {booking['code']}.",
            allow_interruptions=False)
        await handle.wait_for_playout()
        # Returning nothing ends the tool silently, so the model cannot reword the code.


server = agents.AgentServer()


@server.rtc_session(agent_name="clinic-agent")
async def clinic_session(ctx: agents.JobContext) -> None:
    for handler in logging.getLogger().handlers:  # voice-function-tools: PII gate on every sink
        handler.addFilter(_DropPII())
    session = agents.AgentSession(
        # voice-pipeline-choice: cascade, because dates and codes must be exact.
        stt=inference.STT(model="deepgram/nova-3", language="multi"),
        llm=inference.LLM(model="google/gemma-4-31b-it"),
        tts=inference.TTS(model="inworld/inworld-tts-2", voice="Ashley"),
        max_tool_steps=3,
        turn_handling=agents.TurnHandlingOptions(
            # voice-turn-taking: an audio turn model, so the digit case survives.
            turn_detection=inference.TurnDetector(),
            endpointing={"min_delay": 0.3, "max_delay": 2.5},
            # voice-interruptions: two words on a phone line, so mm-hm is not a stop.
            interruption={"min_duration": 0.5, "min_words": 2, "false_interruption_timeout": 2.0},
            preemptive_generation={"enabled": True},
        ),
    )

    @session.on("conversation_item_added")
    def _on_item(ev: agents.ConversationItemAddedEvent) -> None:
        # voice-latency-budget: five timings per turn, never one average.
        m = ev.item.metrics if isinstance(ev.item, ChatMessage) else None
        if not m or ev.item.role != "assistant" or not m.get("e2e_latency"):
            return
        logger.info("turn e2e=%.0fms ttft=%.0fms ttfb=%.0fms", m["e2e_latency"] * 1000,
                    (m.get("llm_node_ttft") or 0) * 1000, (m.get("tts_node_ttfb") or 0) * 1000)

    await session.start(room=ctx.room, agent=ClinicAgent())
    await session.generate_reply(
        instructions="Greet the caller as Riverside Family Medicine, say the call is recorded, "
        "and ask how you can help.")


# Stand-ins for the clinic scheduling API. Replace with the real client.
async def _find_patient(full_name: str, date_of_birth: str):
    return {"id": "p_4417", "physician": "Osei"}

async def _availability(physician: str, date_range: str, kind: str):
    return [{"id": "s_91", "spoken": "Tuesday the fourteenth at three fifteen"}]

async def _book(patient_id: str, slot_id: str, kind: str):
    return {"when": "Tuesday the fourteenth at three fifteen", "physician": "Osei",
            "code": "four seven two one"}


if __name__ == "__main__":
    agents.cli.run_app(server)
