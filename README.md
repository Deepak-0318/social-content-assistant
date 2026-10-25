# Social Content Assistant

An AI-powered application that analyzes uploaded photos and videos,
generates platform-specific social media content, and recommends
posting days and time windows.

## Initial platform support

- Instagram
- Facebook
- YouTube
- Threads
- LinkedIn

## Requirements

- Python 3.12 recommended
- pip
- Git

## Setup

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
cp .env.example .env
```

Run the API:

```bash
uvicorn app.main:app --reload
```

## API documentation

Open http://127.0.0.1:8000/docs

## Run tests

```bash
python -m pytest -q
```
