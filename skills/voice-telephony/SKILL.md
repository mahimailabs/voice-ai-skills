---
name: voice-telephony
description: Put a voice agent on a phone number. Covers SIP trunks and dispatch, inbound versus outbound, answering machine detection and its five outcomes, DTMF keypad input and IVR phone tree navigation, cold versus warm transfer, narrowband audio, recording consent, and outbound calling rules. Use when connecting an agent to PSTN, SIP, Twilio, or Telnyx, when calls hit voicemail, when transfers drop, when callers sound muffled to the STT, or when planning outbound calls.
license: MIT
metadata:
  author: mahimairaja
  version: "0.1.0"
  category: voice-ai
---

# Voice Telephony

This skill decides what changes when the agent runs on a phone line instead of a
browser. It covers the call path, answering machine detection, DTMF, transfers,
narrowband audio, and the outbound calling controls a compliance review will ask for.

## Use this when

- An outbound call reaches voicemail and the agent talks into the recording.
- A transfer drops the caller instead of reaching a person.
- Transcription accuracy falls on the phone but holds up in the browser test.
- The agent must navigate a keypad menu to reach an extension.
- You are moving a working web demo onto a phone number.

## Do not

- Do not greet before answering machine detection returns on an outbound call.
- Do not treat an uncertain detection result as human, and do not deliver the message into it. Probe, then branch.
- Do not attempt a warm transfer with no hold experience. Silence reads as a dropped call.
- Do not assume HD audio. The line is 8 kHz and that changes the STT and the floors.
- Do not record without announcing it in the first agent utterance.
- Do not dial before checking time-of-day rules in the callee's local time zone.
- Do not reuse the inbound prompt for outbound calls. Outbound speaks second, not first.

## The path of a call

`carrier ──> SIP trunk ──> media server ──> room or session ──> agent worker`

- Carrier: the number is unrouted or unported, or the callee's carrier blocks it as spam.
- SIP trunk: authentication fails, or the codec negotiates to something the media path rejects.
- Media server: one-way audio from a NAT or firewall problem on RTP. The call connects, nobody hears anything.
- Room or session: the call lands but no dispatch rule matches, so no agent joins and the caller hears silence.
- Agent worker: no worker has capacity, or it dies mid-call and the line stays open and billing.

Trace a failure from the left. Most reported agent bugs are trunk or media bugs.

## Inbound versus outbound

| what differs | inbound | outbound |
| --- | --- | --- |
| who greets first | the agent, 0.5 s after answer | the callee, then the agent after detection returns |
| answering machine detection | not run | required, and it blocks the first utterance |
| consent | announce recording in the greeting | announce recording, the business, and the purpose |
| time-of-day rules | none, the caller chose the time | a dial window enforced in the callee's local time zone |
| retry policy | none, the caller redials | capped attempts with backoff, logged per number |

Numbers for every knob above are in [references/defaults.md](references/defaults.md).

## Answering machine detection

Detection runs once, on the first utterance after answer. Keep the agent muted until
it returns. Five outcomes, and the agent does something different for each.

| outcome | agent action |
| --- | --- |
| human | proceed with the normal conversation |
| machine IVR | navigate with DTMF to reach a person, or hang up and flag for a human |
| machine voicemail | wait for the beep, speak one self-contained message, hang up |
| machine unavailable | hang up. No message is possible. Schedule a retry |
| uncertain | say a short probe that works either way, keep listening, and branch on what comes back |

The rule on uncertain: say a probe that works whether a person or a machine is
listening, and keep the detector listening. "Hello, this is Riverside Family Medicine."
A reply inside about 1.5 s means a person: continue. Speech that resumes with no reply
means a greeting that paused: it is a machine, so wait for the beep and only then
leave the message. Nothing at all until the no-speech timeout means unavailable:
hang up and retry in the next window. Never deliver the message before a beep or a
reply. A voicemail records only after the beep, so a message spoken into the greeting
is lost twice: the person never heard it and the recording never caught it.

At least one vendor's own guidance says to treat uncertain as human and start a normal
conversation. This skill differs, because the failure is asymmetric. A person who
hears a self-contained message loses nothing and can still answer. A machine that
hears a question records dead air, and the message is never delivered. The same
disagreement is repeated in the adapter below.

The full table, with what each outcome sounds like and the log field to write, is in
[references/amd-and-transfers.md](references/amd-and-transfers.md).

## DTMF

The agent must press digits when it hits a keypad menu, an extension, a phone tree at
a transfer destination, or a callback code. Two failure modes, both silent.

1. In-band tones are unreliable. G.711 carries them, but you do not control transcoding
   on the path, and a compressed codec on any hop (G.729, AMR, GSM, low-bitrate Opus)
   smears them past what a detector accepts, as does noise suppression on your own
   output. Send digits out of band as RTP telephone events (RFC 2833 or RFC 4733).
2. The agent speaks over its own tones. Speech and tones share one output path, so the
   menu hears both and matches neither. Gate speech for the length of the digit string.

Default inter-digit gap 0.15 s, tone 0.1 s. Menus that drop digits want a wider gap,
not louder tones.

## Transfers

Cold transfer. One request, no second leg, no context passed. Once the destination
answers, the agent is gone and has no way back. If the destination does not answer
inside the ring timeout, the transfer fails and the caller stays with the agent, after
a silent wait as long as the timeout. It is the cheapest path.

Warm transfer. The agent puts the caller on hold, dials the destination on a second
leg, briefs the person, then joins the two. It costs a second leg, a hold experience,
and 20 to 40 seconds of caller patience. It is the only option when context matters.

| situation | transfer type |
| --- | --- |
| caller asks for a person, nothing collected yet | cold |
| identity and reason already collected | warm |
| clinical question, complaint, or an angry caller | warm |
| after hours, the destination is a voicemail box | cold |
| the destination may not answer | warm, so the caller can be returned |

Ring timeout is 30 s on either type. When the destination does not answer, the caller
returns to the agent, never to silence. The full decision table, with what the caller
hears and the failure mode for each row, is in
[references/amd-and-transfers.md](references/amd-and-transfers.md).

## Narrowband audio

The phone line is 8 kHz, roughly 300 to 3400 Hz. The energy that separates s, f, and
th sits above that ceiling and is simply gone. Four consequences.

- Pick an STT model trained on 8 kHz telephony. A wideband model fed resampled audio loses digits and names.
- Read back every number. Digit confusions (five and nine, S and F) rise on a narrow line.
- Raise min interruption words from 0 to 2. Line hiss and handling noise clear a duration floor here and produce no words.
- Do not upsample and call it HD. The information above 3400 Hz was never transmitted.

## Compliance as engineering requirements

Each item is implementable and checkable in code review. None of them is advice.

1. Announce recording in the first agent utterance, before any caller audio is written to storage.
2. Gate every outbound dial on a time window evaluated in the callee's local time zone, derived from the number and not the server clock.
3. Check a suppression list before every dial. A do-not-call entry blocks the dial itself, not just the retry.
4. Cap attempts per number per day, and store each attempt with its outcome and its detection category.
5. Identify the calling business and the purpose of the call within the first two sentences outbound, and speak a callback number before the call ends, on a live answer and on a voicemail alike.
6. Redact name, date of birth, and phone number in logs at write time. Never name a room or session after a phone number.
7. Store consent with a timestamp, the channel, and the exact wording used, so the record survives a prompt change.

This is not legal advice. Confirm rules for your jurisdiction.

## The clinic example: the voicemail case

The clinic agent calls Dana Whitfield the day before an appointment. Their voicemail
answers with a bright "Hi" then two seconds of silence. It sounds exactly like a person.

Wrong. The agent greets on answer, detection never runs, and it asks "Hi, is this
Dana?" then waits. The recording captures a question and eight seconds of nothing.
The reminder was never delivered, and the patient no-shows.

Right. The agent stays muted until detection returns. A short greeting followed by
silence lands on uncertain more often than not. So the agent says the probe, "Hello,
this is Riverside Family Medicine," and keeps listening. The greeting resumes: "sorry I
missed your call, leave a message after the tone." No reply arrived, so it is a
machine. The agent waits for the beep, then leaves the message:

"This is Riverside Family Medicine calling about your appointment tomorrow, Tuesday
the fourteenth, at three fifteen with Doctor Osei. Call us back at five five five,
zero one two three to change it."

Had a person said "hello?" inside 1.5 s of the probe, the conversation would have
continued from there. The agent hangs up after 5 s of silence and logs the category.

## Adapters

Vendor mappings in full, with a doc URL per claim, are in
[references/adapters.md](references/adapters.md).

### LiveKit Agents
1.8.x, verified 11 September 2026. `AMD` runs once on the first utterance and locks
playout while it classifies. The categories are `human`, `machine-ivr`, `machine-vm`,
`machine-unavailable`, `uncertain`. The vendor example treats `uncertain` as human.
This skill disagrees: leave the self-contained message. Cold transfer is
`sip.transfer_sip_participant`, `ringing_timeout` default 30.0.
```python
async with AMD(session, participant_identity=identity) as detector:
    result = await detector.execute()
```
https://docs.livekit.io/telephony/features/answering-machine-detection/

### Pipecat
1.0, unversioned docs, checked 11 September 2026. The telephony provider is a
serializer on a websocket transport, not a transport class. `twilio_sample_rate`
defaults to 8000 (mu-law), caller keypresses arrive as `InputDTMFFrame`, and
`auto_hang_up` (default True) requires `call_sid`, `account_sid`, and `auth_token`.
```python
from pipecat.serializers.twilio import TwilioFrameSerializer
serializer = TwilioFrameSerializer(stream_sid=sid, call_sid=call, account_sid=acct, auth_token=tok)
```
No built-in detection or transfer helper is documented: verify against current docs.
https://docs.pipecat.ai/api-reference/server/services/serializers/twilio

### Vapi
Unversioned docs, checked 11 September 2026. `voicemailDetection` is a top-level
assistant field, either `"off"` or a plan object, and `voicemailMessage` is what gets
left on the recording. Plan defaults: `beepMaxAwaitSeconds` 30, `type` `audio`. The
carrier detection plan has a different shape, including `machineDetectionTimeout`
default 30 and `machineDetectionSpeechThreshold` default 2400 ms. Transfers use the
`transferCall` tool, `transferPlan.mode` default `blind-transfer` (cold), with six
warm modes beside it. `sipVerb` default `refer`. `timeout` default 60, on the two
operator-speaks-first modes only. Outbound is `POST /call` with `phoneNumberId` plus
`customer`, or `customers` for a batch.
https://api.vapi.ai/api-json
