"""Shared booking rules; no voice SDK imports or network calls.

The three public tools stay lookup_patient, check_availability, book_appointment.
Booking is two-phase: first speak a protected proposal, then accept a new caller yes.
Replace DemoSchedule with an authenticated client preserving the idempotency contract.
"""

import asyncio
import contextlib
import re
import uuid
from dataclasses import dataclass

TOOL_TIMEOUT = 5.0
FILLER_DELAY = 1.5
INSTRUCTIONS = """\
SPOKEN OUTPUT
You are heard, not read. No markdown, lists, symbols, or emoji in spoken replies.
One idea per sentence, under twenty words. Write spoken numbers as words.
Say three fifteen in the afternoon. Read codes digit by digit.
Never speak IDs, keys, or fields whose names start with silent_.
PERSONA
You are the calm, brief scheduling assistant for Riverside Family Medicine.
You give no clinical advice or triage. For an emergency, direct the caller to emergency services.
TASK
Book appointments. For rescheduling or cancellation, offer the clinic's front desk.
Collect full name and date of birth, read the date back, then call lookup_patient.
Call check_availability. Offer at most three slots and never invent a time or an ID.
CONFIRMATION
Call book_appointment when the caller chooses a slot. The tool reads the proposal aloud.
It writes nothing on that first call. Wait for the caller to answer the proposal.
Only after a new clear yes, call book_appointment with the same identifiers.
The tool speaks the read-back and confirmation code. Do not repeat either yourself.
If the caller corrects anything, obtain the new choice and let the tool read it again.
If a result says the outcome is uncertain, do not claim success or failure or retry a write.
"""


class BookingError(Exception):
    """A short message safe to pass to the language model."""


class StepLimitError(BookingError):
    """End the model/tool loop for this caller turn."""


@dataclass(frozen=True)
class Choice:
    patient_id: str
    slot_id: str
    appointment_type: str


class DemoSchedule:
    """In-memory demonstration, not patient verification or durable storage."""

    def __init__(self):
        self.bookings = {}

    async def find_patient(self, full_name, date_of_birth):
        if full_name.casefold().strip() != "dana whitfield" or date_of_birth != "1980-03-04":
            return None
        return {"id": "p_4417", "name": "Dana Whitfield", "physician": "Osei"}

    async def availability(self, physician, date_range, appointment_type):
        if physician.casefold() not in {"any", "osei"}:
            return []
        return [{"id": "s_91", "spoken": "Tuesday, April fourteenth at three fifteen in the afternoon",
                 "physician": "Osei", "appointment_type": appointment_type}]

    async def book(self, choice, idempotency_key):
        # A real backend must enforce this key atomically, including concurrent requests.
        if idempotency_key not in self.bookings:
            self.bookings[idempotency_key] = {"code": "four seven two one"}
        return self.bookings[idempotency_key]

    async def get_booking(self, idempotency_key):
        return self.bookings.get(idempotency_key)


class Clinic:
    def __init__(self, schedule=None, *, timeout=TOOL_TIMEOUT, filler_delay=FILLER_DELAY):
        self.schedule = schedule or DemoSchedule()
        self.timeout = timeout
        self.filler_delay = filler_delay
        self.patient = None
        self.slots = {}
        self.pending = None
        self.confirmed = False
        self.turn = 0
        self.steps = 0
        self.busy = False
        self.keys = {}
        self.uncertain = set()
        self.completed = {}

    def user_turn(self, text):
        self.turn += 1
        self.steps = 0
        answer = " ".join(re.findall(r"[a-z]+", text.casefold()))
        self.confirmed = self.pending is not None and answer in {
            "yes", "yes please", "yes that is right", "yes that s right", "correct", "that is correct"
        }
        if not self.confirmed:
            self.pending = None

    @contextlib.contextmanager
    def tool(self):
        if self.busy:
            raise BookingError("One request is already running. Wait for its result.")
        self.steps += 1
        if self.steps > 3:
            raise StepLimitError("I am having trouble with the schedule. Please contact the front desk.")
        self.busy = True
        try:
            yield
        finally:
            self.busy = False

    async def call(self, operation, speak):
        """One deadline and at most one interruptible filler on every backend call."""
        async def filler():
            await asyncio.sleep(self.filler_delay)
            await speak("Let me check that.", False)

        task = asyncio.create_task(filler())
        try:
            return await asyncio.wait_for(operation, self.timeout)
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

    async def lookup(self, full_name, date_of_birth, speak):
        with self.tool():
            self.patient = None
            self.pending = None
            self.confirmed = False
            self.slots = {}
            try:
                self.patient = await self.call(self.schedule.find_patient(full_name, date_of_birth), speak)
            except TimeoutError:
                raise BookingError("The patient system is not answering. Please contact the front desk.") from None
            if self.patient is None:
                raise BookingError("No record matched. Please repeat your name and date of birth.")
            return {"say": "I found your record.", "silent_patient_id": self.patient["id"]}

    async def availability(self, physician, date_range, appointment_type, speak):
        with self.tool():
            if self.patient is None:
                raise BookingError("Please give your name and date of birth first.")
            self.pending = None
            self.confirmed = False
            self.slots = {}
            try:
                slots = await self.call(self.schedule.availability(physician, date_range, appointment_type), speak)
            except TimeoutError:
                raise BookingError("The calendar is not answering. Please contact the front desk.") from None
            self.slots = {slot["id"]: slot for slot in slots[:3]}
            return {"slots": [{"silent_slot_id": slot["id"],
                               "say": f"{slot['spoken']} with Doctor {slot['physician']}."}
                              for slot in self.slots.values()],
                    "say": "Choose one of these times." if slots else "No times are open. Please contact the front desk."}

    async def book(self, patient_id, slot_id, appointment_type, speak):
        with self.tool():
            choice = Choice(patient_id, slot_id, appointment_type)
            if self.patient is None or patient_id != self.patient["id"]:
                raise BookingError("Please verify your name and date of birth first.")
            slot = self.slots.get(slot_id)
            if slot is None or slot["appointment_type"] != appointment_type:
                raise BookingError("Please choose one of the offered times first.")
            if choice in self.completed:
                await speak(f"Your confirmation number is {self.completed[choice]['code']}.", True)
                return
            if choice in self.uncertain:
                # Reconcile only; never issue another write after an uncertain outcome.
                booking = await self.reconcile(choice, speak)
            elif self.pending == choice and self.confirmed:
                self.pending = None
                self.confirmed = False  # Consume the yes before yielding to the backend.
                key = self.keys.setdefault(choice, str(uuid.uuid4()))
                self.uncertain.add(choice)
                try:
                    booking = await self.call(self.schedule.book(choice, key), speak)
                except TimeoutError:
                    await speak("I am not sure that went through. Let me check.", False)
                    booking = await self.reconcile(choice, speak)
            elif self.pending == choice:
                raise BookingError("Wait for the caller to answer the read-back before calling again.")
            else:
                self.pending = None
                self.confirmed = False
                turn = self.turn
                await speak(f"{self.patient['name']}, {slot['spoken']} with Doctor {slot['physician']}. Is that right?", True)
                # No receipt, failure, or new turn during playback can arm the gate.
                if turn == self.turn:
                    self.pending = choice
                return
            self.completed[choice] = booking
            self.uncertain.discard(choice)
            await speak(f"You are booked. Your confirmation number is {booking['code']}.", True)

    async def reconcile(self, choice, speak):
        try:
            booking = await self.call(self.schedule.get_booking(self.keys[choice]), speak)
        except TimeoutError:
            booking = None
        if booking is None:
            raise BookingError("I cannot confirm whether it was booked. Please contact the front desk before trying again.")
        return booking


def log_metrics(logger, *, turn_id, role, metrics, scope):
    """Missing values remain null. No names, transcripts, or tool arguments are logged."""
    import json
    names = ("transcription_delay", "end_of_turn_delay", "llm_node_ttft", "tts_node_ttfb", "e2e_latency")
    logger.info("voice_metrics %s", json.dumps({"turn_id": turn_id, "role": role,
                "scope": scope, **{name: metrics.get(name) for name in names}}))
