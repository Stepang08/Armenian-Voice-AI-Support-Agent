# Armenian Bank Voice AI Agent

A LiveKit-based voice agent that answers questions about Armenian bank products **in Armenian**.

## Architecture

| Component | Technology |
|-----------|-----------|
| Speech-to-Text | OpenAI Whisper (whisper-1, language=hy) |
| LLM | GPT-4o-mini + RAG |
| Text-to-Speech | OpenAI TTS (alloy) |
| Voice Activity Detection | Silero (local, free) |
| Vector Database | ChromaDB (local) |
| Embeddings | OpenAI text-embedding-3-small |
| Data Source | afm.am — official Armenian financial market aggregator |

## Data Source

All banking data is scraped from **[afm.am](https://afm.am)** — the official Armenian Financial Market aggregator that covers all 17 licensed Armenian banks with daily-updated rates for deposits, consumer loans, and mortgages. Branch data is maintained manually.

## Prerequisites

- Python 3.11+
- Docker Desktop
- An OpenAI API key → https://platform.openai.com/api-keys

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd armenian-bank-voice-agent
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:

```
OPENAI_API_KEY=sk-...        # Required — get from platform.openai.com
LIVEKIT_URL=ws://localhost:7890
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
CHROMA_DB_PATH=./data/chroma_db
LLM_MODEL=gpt-4o-mini
```

### 3. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip3 install -r requirements.txt
```

### 4. Start LiveKit server

```bash
docker compose up -d
```

### 5. Scrape and ingest banking data

```bash
PYTHONPATH=. python3 scripts/ingest_data.py
```

This fetches live data from afm.am and stores it in ChromaDB. Takes ~30 seconds.

### 6. Start the agent

```bash
PYTHONPATH=. python3 agent/main.py start
```

### 7. Test it

Open a new terminal tab:

```bash
source .venv/bin/activate
PYTHONPATH=. python3 scripts/generate_token.py --room bank-support --identity test-user
```

Copy the token, then:
1. Go to **https://agents-playground.livekit.io**
2. Click **Manual**
3. URL: `ws://localhost:7890`
4. Paste the token
5. Click Connect and speak in Armenian!

## Example questions to try

- *Էvոкаbankи аvандi тоkосаdruyтsы orny е?* (What is Evocabank's deposit interest rate?)
- *Аmерiаbankоум мasнaчyugh kaн Yереvаноум?* (Does Ameriabank have branches in Yerevan?)
- *Varki tоkоsаdruyтs orqan e IDBankоum?* (What is IDBank's loan interest rate?)

## Project Structure

```
├── agent/
│   ├── main.py          # LiveKit agent entrypoint
│   └── prompts.py       # System prompts in Armenian
├── rag/
│   ├── knowledge_base.py  # ChromaDB wrapper
│   ├── retriever.py       # Topic detection + semantic search
│   ├── models.py          # Data models
│   └── scrapers/
│       ├── afm.py         # AFM.am scraper (all 17 banks)
│       └── base.py        # Base scraper class
├── scripts/
│   ├── ingest_data.py     # Run to populate the database
│   └── generate_token.py  # Generate LiveKit test tokens
├── docker-compose.yml     # LiveKit server
├── livekit.yaml          # LiveKit configuration
├── requirements.txt
└── .env.example          # Copy to .env and fill in your keys
```
