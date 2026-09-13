# The Five Rules That Break

The five turn-based habits that stop working on a full-duplex model, each as symptom,
cause, and fix. Read this before porting an agent, not after the first bad call.

## 1. The model will not stop talking

**Symptom.** The caller talks over the agent and the agent keeps going. Or the caller
hangs on a word and the agent stops on your side. The transcript then shows it finished
a sentence the caller never heard. Lowering the interruption thresholds changes nothing.

**Cause.** The connection is server-driven. No client event creates, cancels, or
truncates a response. Turn boundaries belong to the model, so endpointing delays,
minimum interruption duration, and minimum interruption words never reach it. The one
thing you still own is the playback buffer on your own side of the wire.

**Fix.** Keep a VAD and let the session cut playback locally. That stops the audio the
caller hears, which is the part that matters, and it is the whole of what you control.
Accept that the model's context still holds the full turn. If a hard stop on a spoken
segment is a product requirement, this shape is the wrong shape.

## 2. Tools never fire

**Symptom.** Tools are registered, the persona names them, and no tool call arrives.
The model answers from memory or stalls. Nothing raises, and the logs show a normal
turn. In one delegation mode the registered tools are ignored with a warning.

**Cause.** The voice model does not see tools. A separate backend model owns the tool
channel and does the reasoning. Tool descriptions in the voice persona are read as
conversation, not as a schema. The model then talks about calling a tool instead of
calling one. Picking the delegation mode with no tool channel removes tools entirely.

**Fix.** Select the delegation mode that carries a tool channel, and name the backend
model explicitly. Put tool guidance in the backend model's instructions. Leave one
sentence in the voice persona saying which requests to hand off and which to answer
directly. Never restate the tool list in the persona.

## 3. say() raises

**Symptom.** A scripted line raises at runtime. With a separate TTS attached it plays,
but the model speaks at the same time and the two voices overlap on the line.

**Cause.** The duplex connection has no verbatim speech path and no text-only response
modality, so there is no half-cascade to fall back to. The model never receives the
audio a separate TTS produced, so it does not know a line was spoken and does not yield.

**Fix.** Stop scripting speech. Move fixed wording to a channel the caller reads. Or
ask for the line through the reply request and accept a paraphrase. If exact wording is
a requirement, move the agent to a cascade. Attaching a TTS to regain say() buys
overlap, not control.

## 4. The script is paraphrased

**Symptom.** A confirmation number, a dosage, or a street address comes out worded
differently on every call. Read-backs drift. Assertions on exact strings fail at random
in the eval suite while the underlying booking is correct.

**Cause.** Everything you pass is treated as intent, never as text to utter. The model
re-phrases it in its own voice, and that includes digits and dates. There is no
instruction strength, no formatting rule, and no delimiter that changes this.

**Fix.** Remove the exactness requirement from speech. Send codes and dates in a text
message the caller reads back. Have the agent speak only the parts that tolerate
paraphrase. If nothing can move out of speech, change the pipeline shape.

## 5. Context edits are silently dropped

**Symptom.** You rewrite the history, summarize old turns, or swap the system prompt
mid-call, and behavior does not change. No exception is raised. A warning may appear in
the log, and the original content keeps running for the rest of the call.

**Cause.** The startup history is fixed when the connection opens: 128 messages or 8192
rendered tokens, oldest dropped first. After that the history is append-only, and the
persona and the voice are immutable for the life of the connection.

**Fix.** Decide the context before connecting and trim it to the budget yourself. After
start, use the three side channels, 500 tokens per append. A real persona change needs a
new connection. That re-sends the conversation as startup history under the same caps.
Budget the cost before you design a multi-persona flow.
