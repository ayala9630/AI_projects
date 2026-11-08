# MeetSpot — API vs SDK

MeetSpot is a conversational venue-finding project and a practical comparison of building an AI agent with an API-oriented approach and an SDK-oriented approach. The two implementations work with the same venue-search domain so their design and operational trade-offs can be studied side by side.

The project includes a Hebrew, right-to-left chat application, local venue data, agent tools, an example comparison scenario, and offline tests. The goal is to compare implementation choices—not to assume either approach is faster, cheaper, or better without measurements.

## What it does

- Searches the local venue catalog by city, minimum capacity, and required features.
- Retrieves details for a selected venue.
- Provides a weather lookup tool for current conditions in a city.
- Includes code for preparing agent context, working with saved preferences, and recording model usage and execution time.
- Preserves venue source-page metadata in the structured dataset.

## The API and SDK comparison

The project separates its implementation areas into `API/` and `SDK/`, while sharing the venue data and domain tools. This makes it possible to compare the work involved in areas such as:

- Setting up the model interaction and agent loop.
- Defining and dispatching tools.
- Building and managing conversation context.
- Tracking token usage, tool calls, and runtime.
- Testing behavior against the same requests and scenario.

Use the same model, prompts, data, and scenario when collecting measurements. Record actual results in [`REPORT.md`](REPORT.md); mark unavailable metrics as unavailable rather than estimating them. The project does not declare a winner in advance.

## Run the chat application

From the repository root, enter the project directory:

```powershell
cd SDK_vs_API
```

Create and activate a virtual environment, then install the project and application dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt streamlit netfree-unstrict-ssl
```

Create a `.env` file in `SDK_vs_API/` and provide your model-provider credentials and model configuration:

```dotenv
GROQ_API_KEY=your_api_key
GROQ_MODEL=your_model_id
```

Keep `.env` private; do not commit API keys. Start the chat interface with:

```powershell
streamlit run app.py
```

`app.py` is the Streamlit entry point. It displays the MeetSpot chat, keeps the conversation in the Streamlit session, and presents the assistant's venue recommendations.

## Run an implementation from the command line

Run either entry point from the `SDK_vs_API/` directory:

```powershell
python -m API.main
```

```powershell
python -m SDK.main
```

Both prompt for event details and print the agent's response. The model configuration and any provider credentials must be available in the environment.

## Tests and comparison scenario

Run the offline test suite from `SDK_vs_API/`:

```powershell
pytest -q
```

The tests cover preference persistence and request-specific overrides, venue filtering and source-page metadata, unknown-tool handling, cost calculations, and agent-loop termination using a mocked model client.

[`scenario.json`](scenario.json) describes a two-session venue-search scenario. It includes expected checks for capacity filtering, saved city preferences, current-request overrides, weather lookup, venue details, and session completion.

## Project layout

```text
SDK_vs_API/
├── app.py                 # Streamlit chat application
├── API/                   # API-oriented agent and orchestration harness
├── SDK/                   # SDK-oriented agent entry point and tool exports
├── shared/                # Venue data, schemas, parsing, and shared tools
│   └── data/
│       ├── venues.json    # Structured venue catalog
│       ├── venues.pdf     # Source venue document
│       └── memory.json    # Saved preference data
├── results/               # Result files for the comparison
├── tests/                 # Offline automated tests
├── scenario.json          # Example two-session comparison scenario
├── REPORT.md              # Comparison report and measurement template
└── requirements.txt       # Python dependencies
```
