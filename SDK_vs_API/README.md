# Venue Recommendation Agent —&#x20;

## 1. Project Overview

The project implements an agent that recommends venues using structured venue data extracted from a PDF.

The agent supports\:API vs SDK

- Searching venues by city, capacity, and required features.
- Retrieving details for a selected venue.
- Persisting preferences between sessions.
- Building a context containing only relevant information.
- Recording model usage and execution time.
- Running offline tests with a mocked API client.

## 2. Implementation

### API Version

The API implementation manages the agent loop, tool dispatch, conversation history, persistent memory, context construction, and usage measurement directly in Python.

### SDK Version

The SDK implementation must use the SDK required by the assignment. A client library for an API is not equivalent to a full agent SDK.

Describe which responsibilities the SDK handles automatically and which remain implemented in application code.

## 3. Measurements

| Metric                |                     API |                     SDK |
| --------------------- | ----------------------: | ----------------------: |
| Input tokens          |        [measured value] | [measured value or N/A] |
| Output tokens         |        [measured value] | [measured value or N/A] |
| Cache read tokens     | [measured value or N/A] | [measured value or N/A] |
| Cache write tokens    | [measured value or N/A] | [measured value or N/A] |
| Model calls           |        [measured value] |        [measured value] |
| Total cost (USD)      | [measured value or N/A] | [measured value or N/A] |
| Runtime (ms)          |        [measured value] |        [measured value] |
| Tests passed          |         [actual result] |         [actual result] |
| Harness lines of code |          [actual count] |          [actual count] |

All measurements should come from actual executions. Missing provider metrics must be marked N/A rather than estimated.

Record the model identifier, execution date, pricing source, and token rates used for cost calculations.

## 4. Harness Comparison

### Responsibilities saved by the SDK

Describe which responsibilities are handled by the SDK, based on its actual documentation and observed behavior.

### Token usage

Compare input and output token counts using the same scenario. Explain differences using measured results rather than assumptions.

### Direct control in the API version

The API implementation provides direct control over tool dispatch, message construction, context selection, stopping conditions, and application-level metrics.

### Measurement and control in the SDK version

Describe which internal operations can be measured directly and which metrics are unavailable or require additional instrumentation.

## 5. Testing

Report the actual results of the offline test suite for each implementation.

Include tests for:

- Tool execution and tool errors.
- Persistent memory save and load.
- Session-to-session preference persistence.
- Current-request overrides.
- Agent loop termination.
- Token and cost calculations.
- Venue capacity filtering.
- Preservation of source-page metadata.

## 6. Conclusion

Choose the implementation that best fits the project requirements.

Base the decision on measured token usage, runtime, implementation complexity, test coverage, and the amount of control required over the agent loop.

Do not claim that one implementation is more efficient unless the measurements support that conclusion.
