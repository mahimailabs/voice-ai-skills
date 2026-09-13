# Voice function tool defaults

The full tool numbers table, the three clinic tool definitions with their read-back
status, and the error sentence table in full. Vendor-neutral.

## Numbers

| knob | default | range | symptom when wrong |
| --- | --- | --- | --- |
| tool timeout | 5 s | 3 to 8 s | too low: slow backends fail on healthy calls. too high: the caller hangs up before the agent speaks |
| spoken filler starts at | 1.5 s | 1.0 to 2.0 s | too low: the agent fills on tools that were about to return. too high: dead air the caller reads as a dropped call |
| filler length | one sentence, under 8 words | | longer fillers collide with the tool result |
| filler repeats | at most 1 per tool call | 0 to 3 | repeated filler sounds like a stuck loop |
| max tool steps per turn | 3 | 1 to 5 | above this the agent chains calls without speaking |
| read-back gate | required before every write | | no range, this is a rule |
| context carried | full history to a token budget, then a summary of the oldest turns | 4 to 16 thousand tokens | too short: the agent re-asks for the date of birth. too long: time to first token grows. a sliding turn window defeats prompt caching |
| tool count on one agent | 3 to 8 | | above this the model picks wrong under time pressure |
| write retry after timeout | 0 automatic retries | | a retried write books twice |

Fillers stay interruptible. The read-back does not. That split is the whole gate.

A tool timeout is often not a framework setting. Set it wherever the stack allows: a
per-tool option, a server config field, or your own HTTP client. Every tool call has a
deadline and a sentence to say when it expires.

## The three clinic tools

The clinic agent answers the main line for four physicians and books, reschedules, and
cancels appointments. It ships exactly three tools.

### check_availability(physician, date_range, appointment_type)

Read only. No read-back gate. Safe to retry. Counts against the 3-step ceiling.

> Find open appointment slots. Call when the caller asks for a time, a day, or a named
> physician, and call again when a slot you offered was refused. Returns at most three
> slots, in the order the caller should hear them.
>
> physician: the physician's surname, or the word any.
> date_range: the window the caller asked for, as plain dates.
> appointment_type: routine, follow up, or urgent.

Returns a sentence naming at most three slots, plus a silent list of slot identifiers
that the prompt marks as never spoken.

### book_appointment(patient_id, slot_id, appointment_type)

WRITE. READ-BACK GATE APPLIES. Not idempotent. Never async.

> Book one slot for one patient. Call only after the caller has heard the day, date,
> time, and physician read back and has said yes. Never call this to check whether a
> slot is free. Calling it twice books two appointments.
>
> patient_id: from lookup_patient. Never from the caller.
> slot_id: from check_availability. Never invented, never guessed.
> appointment_type: the type used when the slot was found.

Returns one sentence with the confirmation number written as words. On timeout, do not
retry blindly: confirm with a read of the patient's bookings. Make the write idempotent
on patient and slot, so a retry with the same key returns the original confirmation.

### lookup_patient(full_name, date_of_birth)

Read only. No read-back gate. Returns PII, so log fields are redacted.

> Find the patient record. Call once the caller has given both a full name and a date
> of birth. Do not guess a spelling: ask the caller to repeat it. Pass the date of
> birth only after you have read it back one digit group at a time.
>
> full_name: as the caller said it, including any spelling they gave.
> date_of_birth: a date, after read-back.

Returns the patient name and year of birth only. The record identifier is silent and
goes to book_appointment, never to the speaker.

## Error sentences

Write the sentence before the failure happens. Under 20 words, numbers as words, no
identifiers, no provider names, nothing the model has to invent.

| failure | cause | the agent says | then |
| --- | --- | --- | --- |
| timeout | no result inside the 5 s deadline | "The scheduling system is not answering. Do you want to hold while I try again?" | wait for the caller, then one read-only retry |
| timeout on a write | the 5 s deadline expired after the request left | "I am not sure that went through. Give me a moment to check." | confirm with a read of the patient's bookings; retry only with an idempotency key |
| not found | the call succeeded, nothing matched | "I cannot find a record for that name and date of birth. Can you spell the last name?" | one retry, then offer a callback |
| refused | the call succeeded, the request was declined | "That slot is gone. The next one is Wednesday the fifteenth at ten in the morning." | offer the next slot from the same result |
| bad arguments | the model sent a value that failed validation | "Let me check that one more time." | let the model correct and retry once |
| step ceiling hit | 3 tool calls in one turn with no speech | "I am having trouble with the schedule. Let me put you through to the front desk." | stop the turn and transfer |

Never let a stack trace, a provider error string, or a record identifier reach the
model on a failure path. It will be spoken. Return the sentence, log the detail.

## Async and background tools

| case | sync or async | why |
| --- | --- | --- |
| check availability | sync | the caller is waiting on the answer to choose |
| book appointment | sync | the confirmation number must be spoken this turn |
| look up patient | sync | the flow cannot continue without identity |
| send a text confirmation | async | the caller does not need to hear it complete |
| write a call summary | async | it happens after the caller is gone |

An async tool returns a sayable sentence at once. It pushes its result back as a
progress update on the same turn. It still counts against the 3-step ceiling.
