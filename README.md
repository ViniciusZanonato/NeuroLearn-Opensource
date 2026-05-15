# NeuroLearn

Flask-based platform that helps educators identify learning profiles and neurodiversity indicators through questionnaires, AI-generated reports, and behavioral analytics.

## Features

- Role-based auth — separate dashboards for teachers and students
- 67-question NeuroLearn questionnaire across 7 dimensions (Ontopsicology framework)
- AI-generated learning profiles via local Ollama (default) or Google Gemini (optional)
- Teacher panel with student profiles, activities, detailed reports, and behavioral analytics
- Student privacy by design — full profile hypotheses are restricted to teachers only
- Adaptive learning paths matched to student profile type
- Pomodoro-style study schedules with auto-generated sessions
- Virtual assistant with pedagogical guardrails
- Accessibility settings (dark mode, font size, TTS, high contrast, reduced motion)
- Content library (video, audio, games) with accessibility metadata
- Behavior monitoring: time-on-task, error rates, peak activity hours

## Stack

- Python 3.10+ / Flask 3.1
- Flask-SQLAlchemy + SQLite
- Jinja2 templates
- Local AI via Ollama (default) — keeps student data on-premises
- Google Gemini as optional fallback

## Project Structure

```text
.
├── app/
│   ├── __init__.py          # app factory
│   ├── config.py
│   ├── extensions.py
│   ├── models.py            # 13 database models
│   ├── utils/
│   │   ├── ai.py            # Ollama / Gemini integration
│   │   ├── security.py      # auth decorators, validators
│   │   └── monitoring.py    # behavioral logging
│   └── blueprints/
│       ├── auth/            # login, logout, register
│       ├── main/            # landing page
│       ├── professor/       # teacher routes
│       ├── aluno/           # student routes
│       └── relatorios/      # reports
├── tests/                   # pytest smoke suite (34 tests)
├── templates/
├── static/
├── run.py
├── init_db.py
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # edit as needed
python init_db.py
python run.py
```

App runs at `http://127.0.0.1:5000`

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

## Environment Variables

```text
SECRET_KEY=change-this-key
AI_PROVIDER=ollama          # or gemini
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=gemma3:12b
OLLAMA_TIMEOUT=180
GEMINI_API_KEY=             # required only if AI_PROVIDER=gemini
```

By default, NeuroLearn uses a local Ollama instance to avoid sending sensitive student data to external services. Start Ollama and pull a model before use:

```bash
ollama pull gemma3:12b
```

For lower-memory machines, use a smaller model and adjust `OLLAMA_MODEL`.

Gemini is available as an optional provider (`AI_PROVIDER=gemini`). Only use it if your institution's privacy policy permits external data processing.

> **Note:** AI outputs are pedagogical hypotheses and support recommendations — not clinical diagnoses. They do not replace professional assessment or human pedagogical judgment.

## License

MIT
