# Answering Machine Detection and Transfers

The two tables the telephony skill summarizes: the full detection action table and the
full transfer decision table. Both are vendor-neutral. The wire spellings live in adapters.md.

## The detection action table

Detection runs once, on the first utterance after answer, and holds the agent silent
until it returns. Five outcomes, five different actions.

| outcome | what it sounds like | agent action | log field |
| --- | --- | --- | --- |
| human | a short greeting then a pause that invites a reply: "Hello?" | proceed with the normal conversation from the first turn | `amd_category=human`, `amd_delay_ms` |
| machine IVR | a menu prompt, options read in order, a tone: "press one for" | navigate with DTMF to reach a person, or hang up and flag the number for a human callback | `amd_category=machine_ivr`, `ivr_path` |
| machine voicemail | a long greeting, a name, an instruction, then a beep | wait for the beep, speak one self-contained message, hang up | `amd_category=machine_voicemail`, `message_left=true` |
| machine unavailable | "the mailbox is full", "not set up", a carrier tone | hang up. No message is possible. Schedule the retry in the next window | `amd_category=machine_unavailable`, `retry_scheduled_at` |
| uncertain | a short greeting then silence, or no speech at all | say a short probe, keep listening, then branch: a reply means human, resumed speech means machine so wait for the beep, silence to the timeout means unavailable | `amd_category=uncertain`, `transcript`, `resolved_as` |

Rules that apply to every row.

- A self-contained line states who is calling, the one fact that matters, and what to do next. It never asks a question.
- Log the category on every outbound call, including the ones that reached a human. It is the only way to measure the detector.
- Never reclassify mid-call. A caller who pauses is not a machine.
- On uncertain, never deliver the message before a beep or a reply. A probe is not the message.

This repository probes on uncertain and branches on what comes back. At least one
vendor's own example treats it as human and starts a conversation. The failure is
asymmetric: a person who hears a complete message loses nothing and can still reply,
while a machine that hears a question records dead air and the message is lost.

The exact wire values differ per stack, including the hyphenation and the number of
categories. They are adapter facts, so they live in
[adapters.md](adapters.md) with a doc URL each.

## The transfer decision table

| situation | transfer type | what the caller hears | failure mode |
| --- | --- | --- | --- |
| caller asks for a person before giving any details | cold | one sentence, then ringing | the destination answers with no idea who is on the line |
| identity and reason already collected | warm | a hold tone for 20 to 40 s, then a person who already knows | the brief is longer than the call it saves |
| clinical question the agent must not answer | warm | a hold tone, then a clinician who has the question | a cold hand-off makes the caller repeat a symptom |
| complaint or an angry caller | warm | a hold tone, then a person told what went wrong | cold transfer reads as being passed around |
| after hours, destination is a voicemail box | cold | a short line, then the box | a warm transfer briefs a recording |
| destination may not answer | warm | a hold tone, then the agent again | with cold, the caller sits in silence for the whole ring timeout before returning |
| transfer to a keypad extension | cold with DTMF | one sentence, then ringing | tones sent before the tree finishes its prompt are dropped |
| caller wants a callback instead | neither | a confirmation and a time window | a transfer queue nobody staffs |

Rules that apply to every row.

- Ring timeout 30 s on the transfer leg. On no answer the caller returns to the agent, never to silence.
- A warm transfer with no hold audio is a dropped call as far as the caller can tell.
- Say what is about to happen before it happens: "I am connecting you to the front desk now."
- The agent leaves the call after the introduction. Three parties on a line is a support incident.
- Log the destination, the transfer type, the ring duration, and whether it connected.
