# Voice function tool adapters

How the tool rules map onto three stacks, with a doc URL on every claim and the
version each claim was checked against. Nothing here is guessed.

Pinned versions: LiveKit Agents for Python 1.8.x, verified 11 September 2026. Pipecat
1.0, unversioned docs, checked 11 September 2026. Vapi, unversioned rolling API,
checked 11 September 2026.

---

## LiveKit Agents 1.8.x

### Defining a tool

`function_tool` is exported from the top level: `from livekit.agents import
function_tool, Agent, RunContext`. Arguments are inferred from the signature. Parameter
names and type hints become the schema. The docstring becomes the description, and the
function name becomes the tool name.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

The decorator signature is `function_tool(f=None, *, name=None, description=None,
raw_schema=None, flags=ToolFlag.NONE, on_duplicate="allow", duplicate_scope="name")`.
Source: https://github.com/livekit/agents/blob/main/livekit-agents/livekit/agents/llm/tool_context.py

Run context arrives as a `RunContext` parameter, matched by type annotation and not by
name. It exposes `.session`, `.function_call`, `.speech_handle`, and `.userdata`.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

```python
from livekit.agents import RunContext, function_tool

@function_tool()
async def check_availability(
    ctx: RunContext, physician: str, date_range: str, appointment_type: str
) -> str:
    """Find open appointment slots. Returns at most three."""
    return await find_slots(physician, date_range, appointment_type)
```

### Timeouts

There is NO framework-level tool timeout parameter in 1.8.x. The documented guidance
is a best practice: "Set explicit timeouts on your HTTP requests to avoid blocking the
agent indefinitely." Set the 5 s deadline on your own HTTP client. Do not look for a
decorator argument, there is none.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

### Filler speech

`ctx.with_filler(source, *, delay=0, interval=None, max_steps=None)` is an async
context manager on `RunContext`. Defaults: `delay=0` seconds, `interval=None` (plays at
most once), `max_steps=None`. Set `delay=1.5` for the canonical filler. Filler plays
only after the session has been continuously idle for `delay`, so it does not talk over
the caller. It goes through `session.say()` and bypasses the LLM.
Source: https://docs.livekit.io/agents/logic/tools/async.md

```python
async with ctx.with_filler("Let me check that.", delay=1.5):
    slots = await find_slots(physician, date_range, appointment_type)
```

### Async and background tools

`await ctx.update(message)` pushes a progress update into the chat context. The first
update releases control to the LLM with `message` as the tool's synthetic return, and
later updates are coalesced into a deferred reply. A tool becomes non-blocking the
first time it calls `ctx.update(...)`. Tools that never call it stay synchronous.
Source: https://docs.livekit.io/agents/logic/tools/async.md

`ctx.update()` adds to the chat context; `ctx.with_filler()` plays audio directly.
They are different mechanisms and are not substitutes.
Source: https://docs.livekit.io/agents/logic/tools/async.md

`async with ctx.foreground()` drains the pending deferred reply and waits for the
session to be idle. It then holds the floor so no other agent speech interleaves. Use
it to collect a missing detail from inside a background tool.
Source: https://docs.livekit.io/agents/logic/tools/async.md

### Errors

`from livekit.agents import ToolError`. Raising it returns your message to the LLM in
place of a result. Only `ToolError` text reaches the model: any other exception is
replaced by a generic internal-error message, and the original is logged. That is the
mechanism behind the rule that a stack trace must never be spoken.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

Argument validation failures are forwarded to the LLM as a `ToolError`. It carries the
tool name and the validator message. The model can correct and retry with no handling
on your part.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

```python
from livekit.agents import ToolError

if not record:
    raise ToolError(
        "No record for that name and date of birth. Ask the caller to spell the last name."
    )
```

### Duplicate calls and the write path

`@function_tool(on_duplicate=...)` takes `"allow"` (default), `"reject"`, `"replace"`,
or `"confirm"`. Duplicates are detected by tool name only unless you set
`duplicate_scope="name_and_args"`. For `book_appointment`, `on_duplicate="reject"` is
the setting that stops a second write inside one turn.
Source: https://docs.livekit.io/agents/logic/tools/async.md

### Interruptions inside a tool

By default a tool can be interrupted by caller speech but keeps running until it
returns. Python does not auto-cancel. Call `run_ctx.disallow_interruptions()` at the
start of a tool that must not be cut. The alternative is
`await run_ctx.speech_handle.wait_if_not_interrupted([task])`. Then check
`run_ctx.speech_handle.interrupted`, cancel the task yourself, and return `None`.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

### Return values

The return value is converted to a string before it reaches the LLM. Returning `None`
or nothing completes the tool silently with no reply. That is the mechanism for a
background write that should not produce speech.
Source: https://docs.livekit.io/agents/logic/tools/definition.md

### Cancellation

Opt in with `@function_tool(flags=ToolFlag.CANCELLABLE)`. When any cancellable tool is
registered, two companion tools are exposed to the LLM automatically:
`lk_agents_get_running_tasks` and `lk_agents_cancel_task`. Cancelling raises
`asyncio.CancelledError` inside the tool, or `ToolError` if the tool had called
`ctx.disallow_interruptions()`.
Source: https://docs.livekit.io/agents/logic/tools/async.md

---

## Pipecat 1.0

### Defining a tool

The preferred form is a direct function: one async function that is both handler and
schema. The first parameter is always `params: FunctionCallParams` (`from
pipecat.services.llm_service import FunctionCallParams`). The tool arguments follow as
typed keyword parameters. Name, description, properties, and required-ness come from
the signature plus a Google-style docstring. Register by listing the function in
`LLMContext(tools=[...])`. No `register_function` call is needed.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

```python
async def check_availability(params: FunctionCallParams, physician: str):
    """Find open appointment slots.

    Args:
        physician: The physician's surname, or the word any.
    """
    await params.result_callback({"say": "Tuesday the fourteenth at three fifteen."})
```

Return a result with `await params.result_callback(result)`, where `result` is any
JSON-serializable object. Keep it to a sayable sentence plus silent fields.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

`FunctionSchema` is the explicit form: `from pipecat.adapters.schemas.function_schema
import FunctionSchema`, with fields `name`, `description`, `properties`, `required`,
and `handler`. Reach for it when you need a strict `enum`. The direct-function
generator does not yet map `Literal` types to a JSON-schema enum. `appointment_type` is
that case.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

### Timeouts

Per-tool options come from `@tool_options`, imported as `from
pipecat.adapters.schemas.direct_function import tool_options`. Options and defaults:
`cancel_on_interruption=True`, `timeout_secs=None`, `cancellable_by_llm=False`.
`timeout_secs` overrides the LLM service's global `function_call_timeout_secs`. On
timeout the handler is thrown `asyncio.CancelledError`, the call settles as cancelled,
and inference runs so the bot can say it did not complete.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

The default value of the service-level `function_call_timeout_secs` is not stated in
the docs: verify against current docs. Set `timeout_secs=5` per tool instead of relying
on it.

```python
from pipecat.adapters.schemas.direct_function import tool_options

@tool_options(timeout_secs=5)
async def book_appointment(params: FunctionCallParams, patient_id: str, slot_id: str):
    """Book one slot after the caller confirms the read-back."""
    await params.result_callback({"say": "Booked. Confirmation number four seven two one."})
```

Leave `cancel_on_interruption` at its default of `True` on a write. Setting it to
`False` marks the call asynchronous, and a write must not be asynchronous until its
read-back is confirmed. It is also the only state in which `cancellable_by_llm` means
anything. Reach for it on long read-only work, not on the booking call.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

### Gating a write behind a read-back

Change the advertised tool set mid-call by pushing an `LLMSetToolsFrame`. Its `tools`
field takes the same values as `LLMContext(tools=[...])`. Expose `book_appointment`
only after a slot has been chosen, which is the docs' own worked example.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

Protecting the read-back itself needs a mute strategy, not an interruption setting.
Disabling interruptions does not ignore the caller: speech over the bot is still
transcribed and queued. `FunctionCallUserMuteStrategy` mutes the caller during function
calls. Pass it through `LLMUserAggregatorParams(user_mute_strategies=[...])`.
Source: https://docs.pipecat.ai/pipecat/fundamentals/interruptions

### Manual registration

`llm.register_function("check_availability", fetch_slots)` binds a handler by name to a
handler-free `FunctionSchema` listed in the context. It accepts
`cancel_on_interruption`, `timeout_secs`, and `cancellable_by_llm` as direct overrides.
`llm.unregister_function(...)` removes it. Un-advertise the tool with an
`LLMSetToolsFrame` first: unregistering a still-advertised tool leaves the LLM able to
call a missing handler. The docs call manual registration uncommon.
Source: https://docs.pipecat.ai/pipecat/learn/function-calling

---

## Vapi

### Defining a tool

A function tool is `CreateFunctionToolDTO`. Its `type` is the literal `function`. Its
`function` is an `OpenAIFunction`. That holds `name` (up to 64 characters of letters,
digits, underscores and dashes), `description`, `parameters` as a JSON Schema object,
and `strict`, default false. The DTO also carries `server`, `async`, `messages`,
`parameters`, `variableExtractionPlan`, and `rejectionPlan`. Tools attach to the model
block through `tools`, `toolIds`, or `toolRefs`.
Source: https://api.vapi.ai/api-json

`messages` is the array spoken while the tool runs. That is where the 1.5 s filler line
lives on this stack.
Source: https://api.vapi.ai/api-json

### Timeouts

The tool call deadline is `server.timeoutSeconds`, a number with a default of 20
seconds. Lower it to 5. The other `Server` fields are `url`, `headers`, `credentialId`,
`backoffPlan`, `staticIpAddressesEnabled` (default false), and `encryptedPaths`. An
Authorization header here overrides `credentialId` auth. `backoffPlan` defaults to
undefined, which means the request is not retried.
Source: https://api.vapi.ai/api-json

Leave `backoffPlan` undefined on any write. An automatic retry on `book_appointment`
books twice.

### Async tools

`async` defaults to false, which is synchronous. The spec states: "If async, the
assistant will move forward without waiting for your server to respond. This is useful
if you just want to trigger something on your server. If sync, the assistant will wait
for your server to respond." Set `async: true` only for the text confirmation, never
for the booking write.
Source: https://api.vapi.ai/api-json

### Where the tool call lands

The `tool-calls` webhook goes to the first available URL in this order:
`{{tool.server.url}}`, then `{{assistant.server.url}}`, then the phone-number-level
server URL. The body carries the call, assistant, and phone number objects plus the
assistant variables.
Source: https://api.vapi.ai/api-json

### First-party tools for the clinic agent

The Create DTO list includes `CreateFunctionToolDTO`, `CreateApiRequestToolDTO`,
`CreateTransferCallToolDTO`, `CreateHandoffToolDTO`, `CreateEndCallToolDTO`,
`CreateDtmfToolDTO`, `CreateVoicemailToolDTO`, `CreateQueryToolDTO`,
`CreateSmsToolDTO`, `CreateMcpToolDTO`, and calendar tools. For a booking agent,
`GoogleCalendarCheckAvailability` and `GoogleCalendarCreateEvent` map onto
`check_availability` and `book_appointment` without a webhook of your own.
Source: https://api.vapi.ai/api-json

### Testing a write tool

Simulations run unmocked tools for real. The docs warn: "use sandbox integrations or
mock every tool that could create a booking, send a message, or affect a real
customer." Mock `book_appointment` before the first simulation run, not after.
Source: https://docs.vapi.ai/observability/simulations-quickstart
