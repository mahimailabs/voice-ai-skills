---
name: voice-function-tools
description: Design function tools for voice agents. Covers tool descriptions written for spoken intent, confirming arguments before side effects, timeouts and filler speech so the line does not go silent, async and background tools, max tool steps, error strings the agent can say aloud, and context size. Use when adding a tool or function call to a voice agent, when tool calls cause dead air, when the agent books or changes the wrong thing, or when a tool call loops.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Function Tools

This skill decides how a tool call behaves on a live phone line. It sets the deadline,
the filler, the step ceiling, the return shape, and what the agent says on failure.

## Use this when

- Adding a function or tool call to an agent that answers a phone line.
- The line goes silent while a tool runs and the caller says "hello, are you there".
- The agent books, cancels, or reschedules the wrong record.
- A tool call loops: the same tool fires three or four times in one turn.
- A tool returns JSON and the agent reads field names and braces out loud.

## Do not

- Do not let a tool with a side effect run before the caller confirms a read-back.
- Do not return raw JSON. The agent reads the keys aloud and the caller hears noise.
- Do not leave tool timeouts unset. A hung request becomes an open, silent line.
- Do not allow unlimited tool steps in one turn. The agent loops without speaking.
- Do not put the database schema in context. It buys nothing and costs first-token time.
- Do not write a tool description for a reader. Write it for a spoken sentence.
- Do not let the line go silent while a tool runs. Say something by 1.5 seconds.

## How a voice tool differs from a chat tool

1. Silence is a failure mode. A chat tool may take eight seconds with a spinner on
   screen. A silent line at three seconds reads as a dropped call.
2. The result gets spoken. Whatever the tool returns reaches the caller through one
   model hop. Structure in the return value becomes structure in the speech.
3. The caller cannot see a retry. A second attempt is invisible, so a repeated write
   books two appointments and nobody on the call knows it happened.

## Tool descriptions for spoken intent

A tool description is a routing instruction, not documentation. The model matches it
against a sentence somebody said out loud, mid-call. It needs three things: the spoken
triggers, where each argument comes from, and when not to call.

Bad: "Books an appointment in the scheduling system."

That describes the implementation. No trigger phrase, no ordering rule, no guard. The
model fires it while the caller is still choosing a day.

Good: "Book one confirmed slot. Call only after the caller has heard the day, date,
time, and physician read back and has said yes. Never call this to check whether a
slot is free. Calling it twice books two appointments."

## Headline defaults

| knob | default | notes |
| --- | --- | --- |
| tool timeout | 5 s | hard fail after this, with a spoken error |
| spoken filler | starts at 1.5 s | "Let me check that." Nothing longer |
| max tool steps per turn | 3 | above this the agent loops silently |
| read-back gate | required before every write | |
| context | full history to a token budget, then summarize the oldest turns | 8 thousand tokens is safe for a booking call. Never the schema |

A tool timeout is often not a framework setting. On some stacks no such parameter
exists and you set the deadline on your own HTTP client. On others it is a per-tool
option, or a field on the server config that defaults far too high. The rule does not
change: every tool call has a deadline and a sentence to say when it expires.

The full numbers table, the three docstrings, and the error strings are in
[references/defaults.md](references/defaults.md).

## The read-back gate

**No tool with a side effect runs before the caller confirms a read-back, and that
read-back cannot be interrupted.** The gate mechanics belong to [voice-interruptions](../voice-interruptions/SKILL.md).

## The three clinic tools

The clinic agent answers the main line and books, reschedules, and cancels
appointments for four physicians. It needs exactly three tools.

**`check_availability(physician, date_range, appointment_type)`** Read only. No
read-back gate. Safe to retry.

> Find open appointment slots. Call when the caller asks for a time, a day, or a named
> physician, and again when a slot you offered was refused. Returns at most three
> slots. `physician` is a surname or the word any. `date_range` is the window the
> caller asked for. `appointment_type` is routine, follow up, or urgent.

**`book_appointment(patient_id, slot_id, appointment_type)`** WRITE. READ-BACK GATE
APPLIES. Not idempotent.

> Book one slot for one patient. Call only after the caller has heard the day, date,
> time, and physician read back and has said yes. Never call this to check
> availability. Calling it twice books two appointments. `patient_id` comes from
> `lookup_patient`. `slot_id` comes from `check_availability` and is never invented.

**`lookup_patient(full_name, date_of_birth)`** Read only. No read-back gate. Returns
PII, so log fields are redacted.

> Find the patient record. Call once the caller has given both a full name and a date
> of birth. Do not guess a spelling: ask the caller to repeat it. `date_of_birth` is
> passed only after you have read it back one digit group at a time.

## Return values

Return a short sentence, or a small typed object of two or three fields that the
system prompt tells the agent how to speak. Never return the raw record.

The reason is one hop. The tool result goes straight into the model's context and out
of the caller's speaker seconds later. A model under time pressure reads structure
literally, so keys, nulls, and identifiers get spoken.

| return this | not this |
| --- | --- |
| "Three slots. Tuesday the fourteenth at three fifteen with Doctor Osei." | `{"slots":[{"id":"s_91","ts":1760...}]}` |
| "Booked. Confirmation number four seven two one." | `{"ok":true,"conf":"4721","row_id":88213}` |
| "One match. Dana Whitfield, born nineteen eighty." | the full patient record |

Keep identifiers out of the spoken return. The agent needs the slot identifier to pass
into the write, not to say. Return it in a field the prompt marks as silent.

## Errors

Three failure classes cover almost every call. Each one needs a sentence written in
advance, under 20 words, that the agent can say without inventing anything.

| failure | cause | the agent says |
| --- | --- | --- |
| timeout | no result inside the 5 s deadline | "The scheduling system is not answering. Do you want to hold while I try again?" |
| not found | the call succeeded, nothing matched | "I cannot find a record for that name and date of birth. Can you spell the last name?" |
| refused | the call succeeded, the request was declined | "That slot is gone. The next one is Wednesday the fifteenth at ten in the morning." |

Never let a stack trace, a provider error string, or an identifier reach the model on a
failure path. It will be spoken. Return the sentence, log the detail.

On a timeout inside a write, do not retry blindly. The first request may have
committed. Say the timeout sentence, then confirm with a read of the patient's
bookings, not with an availability check: a slot can vanish for other reasons. Better,
make the write idempotent on patient and slot, so a retry returns the original
confirmation instead of a second booking.

## Async and background tools

A tool returns immediately and speaks later in one case. The work outlasts the
caller's patience, and the rest of the call does not depend on the answer. Sending a
text confirmation qualifies. Booking a slot does not.

- Return a sayable sentence now: "I have started that. I will confirm before we hang up."
- Push the result back as a progress update on the same turn, not as a new tool call.
- Never make a write async before its read-back has been confirmed.
- A background tool still counts against the ceiling of 3 tool steps per turn.

Below 1.5 s, say nothing and let the tool finish. Between 1.5 s and the 5 s deadline,
play one filler line and keep it interruptible. Past 5 s, fail and speak.

## Context size

Carry the full history until it passes a token budget, 8 thousand tokens for a booking
call, then summarize the oldest turns into one block and keep the prefix stable so
prompt caching still hits. A sliding window that drops a turn on every turn changes the
prefix on every request and defeats caching. Never the schema. Tool definitions belong
in the tool registry, not pasted into the prompt.

Every token in the prompt is paid for in time to first token. That number sits inside
the 800 ms perceived response budget. A schema dump costs 200 ms and wins nothing: the
model already receives the parameter names in the tool definition.

Keep the tool count at what a caller could plausibly ask for on one line. The clinic
agent ships three. An agent with fifteen tools picks the wrong one under time pressure.

## Adapters

Vendor mappings in full, with a doc URL per claim, are in
[references/adapters.md](references/adapters.md).

### LiveKit Agents
1.8.x, verified 11 September 2026. `@function_tool()` takes the description from the
docstring and the schema from type hints. There is NO framework tool timeout: set it
on your own HTTP client. `raise ToolError("...")` sends your sentence to the model;
any other exception is replaced by a generic internal-error string.
```python
async with ctx.with_filler("Let me check that.", delay=1.5):
    booking = await write_booking(patient_id, slot_id)
```
https://docs.livekit.io/agents/logic/tools/definition.md

### Pipecat
1.0, unversioned docs, checked 11 September 2026. A direct function is handler and
schema at once: first parameter `params: FunctionCallParams`, registered through
`LLMContext(tools=[...])`. Per-tool deadline is `@tool_options(timeout_secs=...)`. For
the service-level `function_call_timeout_secs` default: verify against current docs.
```python
@tool_options(timeout_secs=5, cancel_on_interruption=False)
async def check_availability(params: FunctionCallParams, physician: str) -> None: ...
```
https://docs.pipecat.ai/pipecat/learn/function-calling

### Vapi
Unversioned docs, checked 11 September 2026. A function tool carries `function` (name,
description, JSON Schema parameters), `server`, `async` (default false), `messages`
(spoken while the tool runs), and `rejectionPlan`. The deadline is
`server.timeoutSeconds`, default 20 seconds: lower it to 5.
https://api.vapi.ai/api-json
