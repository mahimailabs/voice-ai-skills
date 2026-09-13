# Pipeline shape comparison

The four shapes across ten dimensions, plus the cost table. Vendor-neutral.

## The matrix

| dimension | cascade | speech-to-speech | half-cascade | full-duplex |
| --- | --- | --- | --- | --- |
| wording control | exact: you write the string the TTS speaks | none: the model paraphrases, numbers included | exact on output: the text is yours | none, and there is no verbatim path at all |
| prosody | flat across sentence boundaries, set by the TTS | best: one model hears and speaks | as good as your TTS, no better | best, plus overlap with the caller |
| latency, p50 end to end | 800 ms ceiling | 500 ms ceiling | no separate canon value: measure it, it lands between the two | 300 ms ceiling |
| cost (re-check current pricing) | lowest of the four | a small multiple of a cascade | cascade plus audio input | 0.05 USD per minute list, plus backend model tokens |
| provider lock-in | low: three stages, each swappable | high: one vendor owns understanding and voice | medium: the voice stage stays yours | highest: one stack ships the model today |
| barge-in control | full: duration floor, word floor, per-utterance gating | partial: the model owns part of the turn logic | full on output, partial on input | none: the model owns turns, a VAD only cuts playback |
| tool support | mature: tools run against the LLM stage | present, and varies by model | present on the text path | delegated to a backend model, not the voice model |
| observability | per-stage timings, so you can name the slow hop | one opaque timing for the whole hop | two timings: model, then TTS | session seconds plus backend tokens |
| language coverage | per stage: pick the best STT for each language | limited to the model's own language list | model's languages in, TTS languages out | the model's language list |
| maturity | highest: the default shape for production today | growing | thin: depends on a text response modality existing | alpha, one stack |

## How to read the latency row

The numbers are the p50 end-to-end ceilings from the shared numbers canon, measured
on a real phone call, not on Wi-Fi. They are ceilings, not targets. The perceived
response target is under 800 ms from the caller's last word to first agent audio.

Half-cascade has no separate canon value on purpose. It is a cascade with a different
first stage, so its budget is the cascade budget with one hop replaced. Measure it.

## Cost per minute

Order of magnitude only. Re-check current pricing before any decision rests on it.

| shape | order of magnitude, per minute | what drives the number |
| --- | --- | --- |
| cascade | cents, low single digits | three metered stages, each billed separately: audio seconds, tokens, characters |
| half-cascade | cascade, plus audio input on the realtime model | audio tokens in, text tokens out, plus TTS characters |
| speech-to-speech | a small multiple of a cascade | audio tokens in and audio tokens out, on one meter |
| full-duplex | 0.05 USD list for the voice model, plus backend model tokens | session seconds billed per second, plus every delegated token |

Re-check current pricing. Every figure above moves, and the ordering between shapes
has inverted before. Price a shape against your own call mix, not against a list rate.

Two costs are missing from every list rate and belong in your own model:

- Failed and abandoned calls still bill for the seconds they used.
- A shape that paraphrases a confirmation number costs a callback, which costs more
  than the call did.

## Choosing under two constraints at once

| constraints | answer |
| --- | --- |
| exact wording plus lowest latency | cascade, then spend the whole order of fixes on it |
| exact wording plus best prosody | half-cascade, and accept the audio-input price |
| lowest latency plus lowest cost | cascade tuned to 800 ms, not a realtime model |
| overlap plus exact wording | no shape does both. Drop one, and drop overlap first |
