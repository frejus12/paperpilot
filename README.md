# PaperPilot AI Research Assistant

PaperPilot is a research assistant for querying and comparing uploaded papers.
The repository is scaffolded according to the project build phases; application
features are being added incrementally.

## Setup

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env`'s example values into your local environment and set
`ANTHROPIC_API_KEY` before using LLM features.

## Run

Start the API in one terminal:

```bash
uvicorn api:app --reload
```

Start the Streamlit interface in a second terminal:

```bash
streamlit run streamlit_app.py
```

Streamlit connects to `http://127.0.0.1:8000` by default. To use a different
API address, set `PAPERPILOT_API_URL` in the environment before starting
Streamlit. The browser only communicates with Streamlit; Streamlit sends the
requests to FastAPI.

The local data directory (`data/`) is gitignored. Run the tests with
`pytest`.

To run the UI and API together with Docker Compose, make sure `.env` exists and
contains the required settings, then run:

```bash
docker compose up --build
```

Open the UI at `http://localhost:8501`. The API is available at
`http://localhost:8000`; inside Compose, the UI connects to the API using the
`api` service name.
