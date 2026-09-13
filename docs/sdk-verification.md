# Clinic SDK verification

Checked September 13, 2026 against **livekit-agents 1.8.1** and **pipecat-ai 1.10.0**.
Official docs establish intended API behavior; imports and fake-I/O tests exercise
those installed releases. This does not certify live model, TTS, or transport behavior.

| Integration | Official source |
| --- | --- |
| LiveKit tools, `RunContext`, `ToolError` | [Tool definition](https://docs.livekit.io/agents/logic/tools/definition/) |
| `say`, per-utterance interruption protection, playout wait | [Speech and audio](https://docs.livekit.io/agents/multimodality/audio/) |
| `on_user_turn_completed` | [Agent nodes](https://docs.livekit.io/agents/logic/nodes/) |
| Message metrics and roles | [Observability data](https://docs.livekit.io/deploy/observability/data/) |
| Pipecat typed tools, deadlines, result callbacks, `run_llm` | [Function calling](https://docs.pipecat.ai/pipecat/learn/function-calling) |
| `TTSSpeakFrame`, exact tool speech and context | [Text to speech](https://docs.pipecat.ai/pipecat/learn/text-to-speech) |
| User mute strategy and suppressed frames | [User input muting](https://docs.pipecat.ai/pipecat/fundamentals/user-input-muting) |
| Assistant turn completion and interruption events | [Interruptions](https://docs.pipecat.ai/pipecat/fundamentals/interruptions) |
| Context access and placement | [Context management](https://docs.pipecat.ai/pipecat/learn/context-management) |
| Input/context gates | [Custom processors](https://docs.pipecat.ai/pipecat/fundamentals/custom-frame-processor) |
| Timing observer callbacks and pipeline timestamps | [Base observer reference](https://reference-server.pipecat.ai/en/latest/api/pipecat.observers.base_observer.html) |
| Service timing data | [Metrics](https://docs.pipecat.ai/pipecat/fundamentals/metrics) |

The installed release source was also inspected for speech completion/error semantics,
assistant aggregation, event scheduling, and frame/metric fields. API references
labeled `latest` can drift; rerun the SDK checks and verify docs when upgrading.
