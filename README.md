# Interview Companion

> AI-powered interview preparation — practice, score, and improve with real-time feedback.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4.1-412991?style=flat&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat)

---

## Overview

Interview Companion is a full-featured interview preparation app built with Streamlit and the OpenAI API. It goes beyond simple Q&A — every answer you give is **automatically scored** on a rubric, your progress is **tracked across the session**, and both questions and feedback are **personalised to your resume and target job description**.

---

## Screenshots

> **To add screenshots:** run the app with `streamlit run app.py`, take a screenshot of each view, and save it to the `screenshots/` folder using the filenames below.

| View | File |
|------|------|
| Landing / empty state | `screenshots/hero.png` |
| Active chat with score card | `screenshots/chat-score.png` |
| Sidebar — profile + tracker | `screenshots/sidebar-tracker.png` |
| Mock interviewer mode | `screenshots/mock-interview.png` |

```
screenshots/
├── hero.png            ← hero section, welcome card, suggestion chips
├── chat-score.png      ← chat with rubric score card below AI response
├── sidebar-tracker.png ← Your Profile + Performance Tracker in sidebar
└── mock-interview.png  ← Mock Interviewer mode with AI avatar
```

---

## Features

### 5 Practice Modes

Each mode uses a distinct prompt engineering technique:

| Mode | Technique | Best for |
|------|-----------|----------|
| **General Q&A** | Zero-Shot | Quick answers to any technical or conceptual question |
| **Behavioral Interview** | Few-Shot + STAR | "Tell me about a time…" answers with structured examples |
| **Deep-Dive Questions** | Chain-of-Thought | Complex problems broken down step by step |
| **Mock Interviewer** | Role-Play | Full simulated interview with turn-by-turn feedback |
| **Question Generator** | Structured Output | Generate ranked question banks by topic and difficulty |

### Answer Scoring

Every substantive answer (15+ words) is automatically scored by `gpt-4.1-nano` on **4 mode-specific dimensions**:

| Mode | Dimensions scored |
|------|-------------------|
| Behavioral | STAR Structure · Specificity · Impact · Relevance |
| Deep-Dive | Technical Accuracy · Problem Decomp. · Trade-offs · Clarity |
| Mock Interview | Completeness · Clarity · Confidence · Relevance |
| General Q&A | Accuracy · Depth · Clarity · Practical Application |

Each answer gets:
- An **overall score** (1–10) with a colour-coded indicator (green / amber / red)
- **Per-dimension bars** with warning icons on weak dimensions
- A **strength** and an **improvement** bullet in plain English

### Performance Tracker

The sidebar tracks running **dimension averages** across the session and surfaces your **weakest focus area** so you know exactly where to drill.

### Personalised to Your Profile

Open the **Your Profile** expander in the sidebar to add:
- **Resume highlights** — the AI calibrates question difficulty and scoring to your actual experience level
- **Job description** — paste the target posting and every question, example, and rubric score is tailored to that exact role

### Voice Input

Click the microphone icon inside the chat bar to record your answer. It is transcribed via **OpenAI Whisper** and sent as your message — no typing required.

### AI Interviewer Avatar

In Mock Interviewer mode, a photorealistic headshot of your AI interviewer is generated via **DALL-E 3** and displayed on the landing screen, unique to each job role.

### Dynamic Suggestion Cards

The three suggestion cards on the landing screen are **generated fresh for your job role** via the API (cached per role/mode pair for performance). Clicking one auto-fills and submits the chat.

### Model & Style Controls

- **5 OpenAI models** selectable via the sidebar: `gpt-4.1-nano` through `gpt-4.1` and `gpt-4o`
- **Response style presets**: Deterministic · Balanced · Creative · Custom (full temperature + top-p sliders)
- **Interviewer persona** (Mock mode only): Neutral · Strict · Friendly
- **Token limit** and frequency/presence penalty controls in Advanced Settings

### Session Stats

Token usage and estimated API cost are tracked per session and displayed in the sidebar.

### Security

- Prompt injection detection (pattern matching on all user inputs and the job role field)
- Input length limits (2000 chars for messages, 3000 for JD)
- API key validation at startup

---

## Setup

### 1. Clone

```bash
git clone https://github.com/lfabijonavicius/Interview-practice-companion.git
cd Interview-practice-companion
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your OpenAI API key

```bash
cp .env.example .env
```

Edit `.env`:

```
OPENAI_API_KEY=sk-...
```

### 4. Run

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Deploying to Streamlit Cloud

1. Push the repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app** → select the repo
3. In **Advanced settings → Secrets**, add:

```toml
OPENAI_API_KEY = "sk-..."
```

4. Click **Deploy**

No `.env` file is needed in production — the app reads from `st.secrets` automatically.

---

## Project Structure

```
interview-practice/
├── app.py                  # Main Streamlit application
├── prompts.py              # System prompts for each mode
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Theme configuration (Zinc 950 dark)
├── components/
│   └── fluid_dropdown/     # Custom React dropdown component
└── screenshots/            # UI screenshots 
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI framework | [Streamlit](https://streamlit.io/) |
| LLM API | [OpenAI](https://platform.openai.com/) — GPT-4.1 / GPT-4o family |
| Answer scoring | OpenAI `gpt-4.1-nano` (structured JSON output) |
| Speech-to-text | OpenAI Whisper via `streamlit-mic-recorder` |
| Image generation | OpenAI DALL-E 3 (interviewer avatar) |
| Env management | [python-dotenv](https://pypi.org/project/python-dotenv/) |
| Custom component | React + Vite fluid dropdown |

---

## Prompt Engineering Techniques

The app was built as a practical demonstration of five distinct prompting strategies:

| Technique | Mode | Description |
|-----------|------|-------------|
| **Zero-Shot** | General Q&A | No examples — model relies on training knowledge |
| **Few-Shot** | Behavioral | Two worked STAR examples prime the response format |
| **Chain-of-Thought** | Deep-Dive | Explicit step-by-step reasoning scaffold |
| **Role-Play** | Mock Interviewer | Persona + strict behavioural rules |
| **Structured Output** | Question Generator | Fixed markdown template enforces consistent formatting |
