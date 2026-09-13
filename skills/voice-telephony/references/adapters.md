# Telephony Adapters

The vendor mapping for every telephony decision in SKILL.md, with a doc URL per claim
and the pinned version. Verify each call against current docs before you ship it.

## Knob mapping

| neutral concept | LiveKit Agents 1.8.x | Pipecat 1.0 | Vapi |
| --- | --- | --- | --- |
| carrier attachment | inbound and outbound SIP trunks plus a DID | a serializer on a websocket transport | a phone number object, `POST /phone-number` |
| inbound routing to an agent | a dispatch rule with `room_config` | your own webhook answering the call | assistant attached to the phone number |
| outbound dial | `CreateSIPParticipant` | your own provider API call | `POST /call` with `phoneNumberId` and `customer` |
| answering machine detection | `AMD`, five categories | verify against current docs | `voicemailDetection`, plan object or `"off"` |
| voicemail message | your own `say` after the beep | verify against current docs | `voicemailMessage` |
| cold transfer | `sip.transfer_sip_participant` | verify against current docs | `transferCall` tool, mode `blind-transfer` |
| warm transfer | `WarmTransferTask` (Beta, Python) | verify against current docs | `transferPlan.mode`, six warm variants |
| send DTMF | `publish_dtmf(code, digit)` | verify against current docs | `CreateDtmfToolDTO` |
| receive DTMF | `sip_dtmf_received` room event | `InputDTMFFrame` | `keypadInputPlan`, fields not verified |
| max call duration | verify against current docs | `idle_timeout_secs` on the worker, default 300 | `maxDurationSeconds` |
| narrowband rate | carrier-negotiated | `twilio_sample_rate`, default 8000 | provider-managed |

## LiveKit Agents

Pinned 1.8.x, verified 11 September 2026.

### Call path

- The services in the path are a DID number, LiveKit server for API requests and trunk
  and dispatch management, and LiveKit SIP to answer SIP requests and match dispatch
  rules. Self-hosting deploys the SIP service separately.
  Source: https://docs.livekit.io/telephony/
- Inbound creates a SIP participant automatically for each caller. Outbound requires an
  explicit `CreateSIPParticipant` call.
  Source: https://docs.livekit.io/telephony/
- Dispatch rule types: `SIPDispatchRuleDirect` (all callers into one room, optional
  `pin`), `SIPDispatchRuleIndividual` (a room per caller, optional `room_prefix`), and
  the callee rule (rooms named after the called number).
  Source: https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/
- PII trap: an individual dispatch rule names each room after the caller's phone
  number. Room names reach logs and traces and are not removed by PII redaction. Use a
  prefix and a random suffix, and keep the number out of the room name.
  Source: https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/
- Supported: SIP over UDP, TCP and TLS, DTMF (RFC 2833 and RFC 4733), cold transfer via
  REFER, warm transfer, caller ID, OPTIONS, RTP, SRTP. Not supported: SIP REGISTER,
  SIPREC, video over SIP.
  Source: https://docs.livekit.io/telephony/

### Detection

`AMD` runs once at the start of the call, on the first user utterance, and does not
monitor continuously. While it runs, speech playout authorization is locked, so the
agent cannot talk over a voicemail greeting.
Source: https://docs.livekit.io/telephony/features/answering-machine-detection/

```python
from livekit.agents import AMD

async with AMD(session, participant_identity=identity) as detector:
    await ctx.api.sip.create_sip_participant(...)
    result = await detector.execute()
    if result.category == "machine-vm":
        ...
```

The five categories, exactly: `human`, `machine-ivr`, `machine-vm`,
`machine-unavailable`, `uncertain`. They are hyphenated abbreviations on the wire.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/amd/classifier.py

Constructor flags: `interrupt_on_machine` default True, `ivr_detection` default True
(the session starts IVR navigation itself in Python), `wait_until_finished` default
True. `detection_options` defaults, in seconds: `human_speech_threshold` 2.5,
`human_silence_threshold` 0.5, `machine_silence_threshold` 1.5, `no_speech_threshold`
10.0, `timeout` 20.0, `max_endpointing_delay` 3.0.
Source: https://docs.livekit.io/telephony/features/answering-machine-detection/

The result is an `AMDPredictionEvent` with `category`, `reason`, `transcript`,
`speech_duration`, `delay`, plus `is_human` and `is_machine`. Log `category` and
`delay` on every outbound call.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/amd/classifier.py

Disagreement, repeated from SKILL.md. The vendor documents `uncertain` as "Treat as a
human and proceed with normal conversation", and its own example branches
`if result.category == "human" or result.category == "uncertain"`. This repository does
the opposite for message-delivery calls: on `uncertain`, speak one self-contained line
and wait. A person loses nothing. A machine would otherwise record a question.
Source: https://docs.livekit.io/telephony/features/answering-machine-detection/

### Transfers

Cold transfer is on the SIP service client, not the room service. It sends a SIP REFER
through the trunk and the caller leaves the room, ending the session. `ringing_timeout`
defaults to 30 seconds; on timeout the request errors and the caller stays in the room.
Errors surface as `api.SipCallError` (`sip_status_code`, `sip_status`). Caller ID is
configured on the trunk and cannot be set per transfer.
Source: https://docs.livekit.io/telephony/features/transfers/cold/

```python
from livekit import api, rtc

sip = next(p for p in job_ctx.room.remote_participants.values()
           if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP)
await lkapi.sip.transfer_sip_participant(api.TransferSIPParticipantRequest(
    participant_identity=sip.identity, room_name=room, transfer_to=number,
    play_dialtone=False, ringing_timeout=30.0))
```

The participant identity is assigned at dispatch time and may differ from the phone
number, so filter the remote participants on SIP kind instead of guessing it.
Source: https://docs.livekit.io/telephony/features/transfers/cold/

Warm transfer is `WarmTransferTask` from `livekit.agents.beta.workflows`, labeled Beta
and Python only. The flow is five steps: hold the caller, dial the manager into a
private consultation room, brief them, connect them to the caller, then leave.
`hold_audio` covers the hold experience and `ringing_timeout` caps the dial. Each `w`
in `dtmf` pauses about 0.5 s.
Source: https://docs.livekit.io/telephony/features/transfers/warm/

### DTMF

```python
await local_participant.publish_dtmf(code=1, digit="1")
await local_participant.publish_dtmf(code=11, digit="#")

@room.on("sip_dtmf_received")
def on_dtmf(dtmf: rtc.SipDTMF):
    log.info("dtmf", extra={"code": dtmf.code, "digit": dtmf.digit})
```

Tones travel over RTP as `telephone-event/8000` (RFC 2833 and RFC 4733), which is the
out-of-band path SKILL.md requires. `AgentSession(ivr_detection=True)` relays caller
digits automatically, and `GetDtmfTask` accepts both tones and spoken digits.
Source: https://docs.livekit.io/telephony/features/dtmf/

## Pipecat

Pipecat 1.0. Unversioned docs, checked 11 September 2026.

The telephony provider is a serializer on a websocket transport, not a transport class.
Pair `TwilioFrameSerializer` with `FastAPIWebsocketTransport` and
`FastAPIWebsocketParams`.
Source: https://docs.pipecat.ai/api-reference/server/services/serializers/twilio

```python
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport

serializer = TwilioFrameSerializer(
    stream_sid=stream_sid, call_sid=call_sid,
    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
)
```

`InputParams` defaults: `twilio_sample_rate` 8000, `sample_rate` None (falls back to
the pipeline rate), `auto_hang_up` True, `ignore_rtvi_messages` True,
`resampler_clear_after_secs` 0.2. Set that last one to `None` for providers with
irregular gaps. With `auto_hang_up=True` the constructor raises `ValueError` unless
`call_sid`, `account_sid` and `auth_token` are all supplied. The audio is 8 kHz mu-law
(PCMU) and the serializer converts to and from PCM. Caller keypresses arrive as
`InputDTMFFrame`.
Source: https://docs.pipecat.ai/api-reference/server/services/serializers/twilio

Narrowband detail: `SileroVADAnalyzer` takes `sample_rate` of 8000 or 16000, 256
samples per frame at 8 kHz. Match it to the line rather than resampling for it.
Source: https://docs.pipecat.ai/api-reference/server/services/vad/silero-vad-analyzer

The narrowband word floor is `MinWordsUserTurnStartStrategy(min_words=2)` from
`pipecat.turns.user_start`. The threshold applies only while the bot is speaking.
Source: https://docs.pipecat.ai/server/utilities/turn-management/user-turn-strategies

The call length cap is `idle_timeout_secs` on `PipelineWorker`, default 300, with
`cancel_on_idle_timeout` default True. That is an idle cap, not a wall-clock call cap.
Source: https://docs.pipecat.ai/server/pipeline/pipeline-task

Answering machine detection, cold transfer and warm transfer: no built-in helper
appears in the docs checked. Verify against current docs before assuming there is none.

## Vapi

Unversioned docs, checked 11 September 2026. Facts from the live OpenAPI spec.

### Detection

`voicemailDetection` is a top-level assistant field. It is either the literal string
`"off"` or a plan object discriminated by `provider`, with four providers available.
`voicemailMessage` holds what gets left on the recording. A separate voicemail tool
gives the assistant explicit control over deciding it reached voicemail.
Source: https://api.vapi.ai/api-json

| field | default | note |
| --- | --- | --- |
| `beepMaxAwaitSeconds` | 30 | max wait from call start for the beep before speaking |
| `type` | `audio` | `audio` uses native audio models, `transcript` uses ASR |
| `backoffPlan` | none | retry shaping |

The carrier-backed plan has a different shape: `enabled` default true,
`voicemailDetectionTypes` default `['machine_end_beep', 'machine_end_silence']`,
`machineDetectionTimeout` 30 s, `machineDetectionSpeechThreshold` 2400 ms (longer reads
as a machine), `machineDetectionSpeechEndThreshold` 1200 ms,
`machineDetectionSilenceTimeout` 5000 ms.
Source: https://api.vapi.ai/api-json

There is no five-way outcome enum here. Map the neutral outcomes onto the plan you
choose, and keep the uncertain rule in your own prompt and message text.

### Transfers

The tool `type` is the exact string `"transferCall"`, carrying a `destinations` array.
With no destinations, the transfer target is fetched from `server.url` when the tool
fires. Destination shapes are number, SIP, and assistant. With no `message` set, the
default spoken line is "Transferring the call now".
Source: https://api.vapi.ai/api-json

```python
transfer_tool = {
    "type": "transferCall",
    "destinations": [{
        "type": "number", "number": "+15555550123", "extension": "204",
        "message": "Connecting you to the front desk now.",
        "transferPlan": {"mode": "warm-transfer-say-summary"},
    }],
}
```

`transferPlan.mode` defaults to `blind-transfer`, which is the cold path. Seven other
modes exist, including `blind-transfer-add-summary-to-sip-header`,
`warm-transfer-say-message`, `warm-transfer-say-summary`, two operator-speaks-first
variants, `warm-transfer-twiml`, and `warm-transfer-experimental` (holds the customer,
dials, and falls back to `fallbackMessage` when the destination is not human).
Source: https://api.vapi.ai/api-json

Other transfer fields: `timeout` default 60 (operator-speaks-first modes), `sipVerb`
default `refer` from `['refer', 'bye', 'dial']`, `dialTimeout` default 60 (only with
`sipVerb: dial`), `sipHeadersInReferToEnabled` default false, plus `holdAudioUrl` and
`transferCompleteAudioUrl`, which are the hold experience SKILL.md requires.
Source: https://api.vapi.ai/api-json

### Outbound and call controls

Outbound is `POST /call` with `assistantId` or a transient `assistant`, plus
`phoneNumberId` and `customer`. Pass `customers` as an array for a batch, and
`schedulePlan` to schedule. Phone numbers are managed at `POST /phone-number` and
`GET|PATCH|DELETE /phone-number/{id}`, and phone-number-level hooks support the
`call.ringing` event.
Source: https://api.vapi.ai/api-json

Call caps and recordings: `maxDurationSeconds` is a top-level assistant field.
Recordings are fetched per call at `/call/{id}/mono-recording`, `/stereo-recording`,
`/customer-recording`, `/assistant-recording`, and `/pcap`.
Source: https://api.vapi.ai/api-json

`compliancePlan` and `keypadInputPlan` are top-level assistant fields. Their inner
field names and defaults are not in the docs checked: verify against current docs before
relying on either for recording consent or DTMF capture.
Source: https://api.vapi.ai/api-json

## Detection result spellings

The wire values differ from the plain-English names above. LiveKit Agents spells them
`human`, `machine-ivr`, `machine-vm`, `machine-unavailable`, `uncertain` (hyphenated,
and there is no category named "machine greeting").
Source: https://docs.livekit.io/telephony/features/answering-machine-detection/

Vapi has no five-way result. It exposes a `voicemailDetection` plan
plus a `voicemailMessage` to leave, and its carrier-backed plan reports on a different
axis, with `voicemailDetectionTypes` defaulting to `['machine_end_beep',
'machine_end_silence']`.
Source: https://api.vapi.ai/api-json
