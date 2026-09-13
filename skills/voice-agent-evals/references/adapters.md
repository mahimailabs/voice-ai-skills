# Adapters

Per-stack mappings for the eval rules in SKILL.md, with a doc URL on every claim and
the version each claim was checked against. These drift. Re-verify before you ship.

## LiveKit Agents

Pinned to livekit-agents 1.8.1 (Python), docs rendered 11 September 2026. Simulations
need LiveKit CLI v2.16.4 or later, and v2.18.3 or later for audio runs.

### The eight judges

`livekit.agents.evals` exports exactly `EvaluationResult`, `Evaluator`, `JudgeGroup`,
`Judge`, `JudgmentResult`, `Verdict`, and eight factory functions: `accuracy_judge`,
`coherence_judge`, `conciseness_judge`, `handoff_judge`, `relevancy_judge`,
`safety_judge`, `task_completion_judge`, `tool_use_judge`. Each is called with parens.
`handoff_judge()` passes automatically when no handoff occurred.
Source: https://docs.livekit.io/agents/start/testing/test-framework.md

`JudgeGroup(llm=..., judges=[...])` takes keyword arguments only. `llm` accepts an LLM
instance or a model string routed through LiveKit Inference. `JudgeGroup` and
session-scoped `mock_tools` are Python only, not Node.js.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/evals/evaluation.py

```python
from livekit.agents.evals import JudgeGroup, accuracy_judge, relevancy_judge
from livekit.agents.evals import task_completion_judge, tool_use_judge

judges = JudgeGroup(
    llm="openai/gpt-4o-mini",
    judges=[task_completion_judge(), accuracy_judge(), tool_use_judge(), relevancy_judge()],
)
result = await judges.evaluate(session.history)
assert result.all_passed, f"Some judges failed: {result.judgments}"
```

`EvaluationResult` carries `score` (1.0 pass, 0.5 maybe, 0.0 fail), `all_passed`,
`any_passed`, `majority_passed`, `none_failed`, and `judgments` keyed by judge name.
Each `JudgmentResult` has `verdict`, `reasoning`, and `passed` / `failed` / `uncertain`.
Source: https://docs.livekit.io/agents/start/testing/test-framework.md

### Assertions

`await session.run(user_input="...")` returns a `RunResult`. `user_input` is
keyword-only, and `input_modality` defaults to `"text"`. Walk the events with
`result.expect.next_event(type="message" | "function_call" | "function_call_output" |
"agent_handoff")`, close with `result.expect.no_more_events()`, and assert with
`is_message(role=...)`, `is_function_call(name=...)`, `is_function_call_output()`, or
`contains_message(role=...)`. Indexing works too: `result.expect[0:2]`.
Source: https://docs.livekit.io/agents/start/testing/test-framework.md

Per-message judging is `await ...judge(llm, intent="...")`: the LLM is positional,
`intent` is keyword-only, and the message is judged without surrounding context.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/run_result.py

### Custom deterministic judge

Subclass `Judge`, call `super().__init__(name="...")`, and override
`async def evaluate(self, *, chat_ctx, reference=None, llm=None) -> JudgmentResult`.
No model call is required inside it. Any object with a `name` property and that
`evaluate` signature satisfies the `Evaluator` protocol and can sit in a `JudgeGroup`.
Source: https://docs.livekit.io/agents/start/testing/test-framework.md

```python
from livekit.agents.evals import Judge, JudgmentResult

class ConfirmationNumberJudge(Judge):
    def __init__(self) -> None:
        super().__init__(name="confirmation_number")

    async def evaluate(self, *, chat_ctx, reference=None, llm=None) -> JudgmentResult:
        found = any("CONF-" in (i.text_content or "") for i in chat_ctx.items)
        return JudgmentResult(verdict="pass" if found else "fail", reasoning="")
```

### Mocking write tools

`mock_tools(agent_class, mocks, *, session=None)` imports from `livekit.agents`.
Without `session` it is a context manager for tests. With `session=session` it applies
for the session lifetime; pass `{}` to clear. Mocks intercept execution only, so the
model still sees the real schema. Returning an exception instance makes the tool raise.
In Python the mock receives only the parameters it declares.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/voice/run_result.py

```python
from livekit.agents import mock_tools

with mock_tools(ClinicAgent, {"book_appointment": lambda: RuntimeError("booking down")}):
    result = await session.run(user_input="Book me Tuesday at three fifteen.")
    await result.expect.next_event(type="message").judge(
        llm, intent="Says the booking system failed and offers a callback."
    )
```

### Text and audio simulation

Text is the default mode for `lk agent simulate`; there is no `--text` flag, and a
text run automatically disables STT, TTS, VAD, and audio input and output.
Top-level options: `-n/--num-simulations`, `--scenarios <file>`, `--concurrency <n>`
(defaults to 15, explicit maximum 20, project limit 30), `--agent-name <name>`
(requires `--scenarios`), `-y/--yes`, `--view <run-id>`, `--export <run-id>`.
Source: https://docs.livekit.io/agents/start/testing/simulations.md

Audio is a subcommand: `lk agent simulate audio --scenarios scenarios.yaml`. The
simulated user joins the room and publishes an audio track, your STT, TTS, and VAD run
and are billed, and the run executes in real time. Three degradation flags exist and
are boolean, with no intensity argument: `--background-noise` (surfaces endpointing
that triggers on noise), `--low-quality-microphone` (surfaces transcription errors on
names, numbers, and codes), `--packet-loss` (surfaces clipped speech handling).
Source: https://docs.livekit.io/agents/start/testing/simulations.md

There is NO accent flag and no voice-selection option. The scenario file has exactly
five fields: `label`, `instructions`, `agent_expectations`, `tags`, `userdata`. Put the
accent in the free-text `instructions` persona. Treat accent simulation as unavailable.
Source: https://docs.livekit.io/agents/start/testing/simulations.md

An audio run reports end-to-end latency at p50, p95, and p99 (negative means the agent
talked over the caller) and breaks it down by stage: STT and endpointing delay, LLM
time to first token and first sentence, tokens per second, and TTS time to first byte.
That is the latency number to publish beside the pass rate.
Source: https://docs.livekit.io/agents/start/testing/simulations.md

### Latency in production runs

Per-turn latency is on `ChatMessage.metrics`, read from the `conversation_item_added`
event. Keys include `end_of_turn_delay`, `transcription_delay`, `llm_node_ttft`,
`tts_node_ttfb`, and `e2e_latency`. `MetricsReport` is a total=False TypedDict, so read
every key with `.get()`. The session-level `metrics_collected` event is deprecated.
Source: https://docs.livekit.io/deploy/observability/data/

## Pipecat

Pipecat 1.0 docs, unversioned page set, checked 11 September 2026.

No scenario harness, simulated caller, or shipped judge set is confirmed for Pipecat in
this fact set. Verify against current docs before claiming one exists. Until then,
drive scenarios from your own test runner and assert on frames and tool calls.

Latency and usage come from the pipeline metrics. Set `enable_metrics=True` and
`enable_usage_metrics=True` on `PipelineParams` (both default False) and attach
`MetricsLogObserver`. Five metrics are logged: TTFB, TTFA (TTS only), TTFAT (LLM only),
Processing Time, and Text Aggregation. Usage metrics are per interaction, not totals.
Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

```python
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.observers.loggers.metrics_log_observer import MetricsLogObserver

worker = PipelineWorker(
    pipeline,
    params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
    observers=[MetricsLogObserver()],
)
```

Filter with `MetricsLogObserver(include_metrics={LLMUsageMetricsData, TTSUsageMetricsData})`,
or isinstance-check `MetricsFrame` in a custom `FrameProcessor`. The data classes live
in `pipecat.metrics.metrics`.
Source: https://docs.pipecat.ai/pipecat/fundamentals/metrics

Two facts that change what a scenario can assert. Disabling interruptions does not
ignore the caller: speech over the bot is still transcribed and queued, so a read-back
scenario needs a mute strategy, not an interruption setting. And a per-tool deadline is
`@tool_options(timeout_secs=...)`, default `None`, overriding the LLM service's
`function_call_timeout_secs`, whose default is not stated: verify against current docs.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

## Vapi

Unversioned rolling API, checked 11 September 2026 against the live OpenAPI spec.

Two separate testing products, not one.
Evals: mock conversations with response validation and tool-call checks, pass or fail.
Endpoints `POST|GET /eval`, `GET|PATCH|DELETE /eval/{id}`, `POST|GET /eval/run`,
`GET|DELETE /eval/run/{id}`.
Simulations: an AI tester holds a real conversation with your assistant or squad, under
`/eval/simulation/`.
Source: https://api.vapi.ai/api-json

Simulation object model: a scenario (name plus intent prompt) pairs with a personality
(the AI tester) to form a simulation. One or more simulations form a suite. Running a
suite produces a run with per-simulation items. Endpoints include
`/eval/simulation/personality`, `/eval/simulation/scenario`,
`/eval/simulation/scenario/generate`, `/eval/simulation/suite`, `/eval/simulation/run`,
and `/eval/simulation/concurrency`.
Source: https://api.vapi.ai/api-json

Success is defined by structured outputs: a name, a type such as Boolean, a description
stating the pass condition, a comparator such as equals, and an expected value. At
least one structured output is required before a simulation can run. Runs execute in
Chat mode (no speech or transcription, faster and cheaper) or Voice mode (speech,
transcription, and turn-taking with a synthetic caller), with configurable Iterations.
Run status moves queued, then running, then ended.
Source: https://docs.vapi.ai/observability/simulations-quickstart

Two warnings that matter for a booking agent. The docs state verbatim: "Simulations run
unmocked tools for real. Before running, inspect [the assistant's] tools and use sandbox
integrations or mock every tool that could create a booking, send a message, or affect a
real customer." And a voice-mode criterion "doesn't grade pronunciation, pauses, or
interruptions", so a Voice-mode pass is not an audio pass by this skill's definition.
Source: https://docs.vapi.ai/observability/simulations-quickstart

The exact JSON request bodies for creating a scenario, personality, simulation, suite,
and run are not confirmed here: verify against current docs.
