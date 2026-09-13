"""Clinic appointment booking agent on LiveKit Agents 1.8.

Run: uv run --with "livekit-agents==1.8.1" --with python-dotenv livekit_agent.py dev
Each choice is a rule from skills/. README.md maps code to skill. Verified against
LiveKit Agents 1.8.1 on 13 September 2026. Re-check the API before you ship this.
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

from clinic import BookingError, Clinic, INSTRUCTIONS, log_metrics


class ClinicAgent(agents.Agent):
    def __init__(self) -> None:
        super().__init__(instructions=INSTRUCTIONS)
        self.clinic = Clinic()

    async def on_user_turn_completed(self, turn_ctx, new_message: ChatMessage) -> None:
        self.clinic.user_turn(new_message.text_content or "")

    async def speak(self, text: str, protected: bool) -> None:
        handle = self.session.say(text, allow_interruptions=not protected)
        if protected:
            # Authorization is armed only when the exact proposal finished playing.
            try:
                await asyncio.wait_for(handle.wait_for_playout(), 30)
            except asyncio.TimeoutError:
                raise BookingError("I could not finish the read-back. Please contact the front desk.") from None
            if handle.interrupted or handle.exception():
                raise BookingError("The read-back did not finish. Please ask me to repeat it.")

    async def invoke(self, operation):
        try:
            return await operation
        except BookingError as error:
            raise agents.ToolError(str(error)) from None
        except Exception:
            # Do not leak backend exceptions or claim an uncertain write failed.
            raise agents.ToolError("The request could not be confirmed. Please contact the front desk before trying again.") from None

    @agents.function_tool()
    async def lookup_patient(self, context: agents.RunContext, full_name: str, date_of_birth: str) -> dict:
        """Find the caller after reading back their date of birth.

        Args:
            full_name: The caller's full name.
            date_of_birth: Confirmed date in YYYY-MM-DD format.
        """
        return await self.invoke(self.clinic.lookup(full_name, date_of_birth, self.speak))

    @agents.function_tool()
    async def check_availability(self, context: agents.RunContext, physician: str,
                                 date_range: str, appointment_type: str) -> dict:
        """Find up to three times; keep the silent slot IDs for booking.

        Args:
            physician: Requested physician, or any.
            date_range: Requested date window.
            appointment_type: routine, follow up, or urgent.
        """
        return await self.invoke(self.clinic.availability(physician, date_range, appointment_type, self.speak))

    @agents.function_tool()
    async def book_appointment(self, context: agents.RunContext, patient_id: str,
                               slot_id: str, appointment_type: str) -> None:
        """First call speaks the proposal without writing. Call again only after a new yes.

        Args:
            patient_id: silent_patient_id from lookup_patient.
            slot_id: silent_slot_id of the caller's chosen time.
            appointment_type: The appointment type used in check_availability.
        """
        await self.invoke(self.clinic.book(patient_id, slot_id, appointment_type, self.speak))


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
            # Complete the user-turn authorization hook before any speculative tools.
            preemptive_generation={"enabled": False},
        ),
    )

    @session.on("conversation_item_added")
    def _on_item(ev: agents.ConversationItemAddedEvent) -> None:
        if isinstance(ev.item, ChatMessage) and ev.item.role in {"user", "assistant"}:
            log_metrics(logger, turn_id=ev.item.id, role=ev.item.role,
                        metrics=ev.item.metrics or {}, scope="livekit_message_seconds")

    await session.start(room=ctx.room, agent=ClinicAgent())
    await session.generate_reply(
        instructions="Greet the caller as Riverside Family Medicine, "
        "and ask how you can help.")


if __name__ == "__main__":
    agents.cli.run_app(server)
