import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import io
import json
from streamlit_mic_recorder import mic_recorder

from prompts import PROMPTS

load_dotenv()

MAX_INPUT_LENGTH = 2000
MAX_ROLE_LENGTH = 60

# Known prompt injection / jailbreak patterns (case-insensitive substring match)
_INJECTION_PATTERNS = [
    "ignore previous", "ignore above", "ignore all", "ignore instructions",
    "forget previous", "forget everything", "forget above",
    "you are now", "act as", "pretend to be", "roleplay as",
    "new instructions", "override", "disregard",
    "system prompt", "jailbreak", "dan mode", "developer mode",
    "do anything now", "no restrictions", "without restrictions",
    "bypass", "unlock mode", "unfiltered",
]


def _is_injection(text: str) -> bool:
    """Return True if text contains a known prompt injection pattern."""
    lower = text.lower()
    return any(p in lower for p in _INJECTION_PATTERNS)


def _transcribe_audio(openai_client, audio_bytes: bytes) -> str:
    """Transcribe audio bytes via OpenAI Whisper. Returns the transcript or ''."""
    buf = io.BytesIO(audio_bytes)
    buf.name = "recording.wav"
    try:
        result = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
        )
        return result.text.strip()
    except Exception as e:
        st.error(f"⚠️ Transcription failed: {e}")
        return ""

MODEL_OPTIONS = ["gpt-4o-mini", "gpt-4o", "gpt-4.1-nano", "gpt-4.1-mini", "gpt-4.1"]

MODEL_LABELS = {
    "gpt-4o-mini":  "GPT-4o mini",
    "gpt-4o":       "GPT-4o",
    "gpt-4.1-nano": "GPT-4.1 nano",
    "gpt-4.1-mini": "GPT-4.1 mini",
    "gpt-4.1":      "GPT-4.1",
}

MODEL_COSTS = {
    "gpt-4o-mini":  {"input": 0.15,  "output": 0.60},
    "gpt-4o":       {"input": 2.50,  "output": 10.00},
    "gpt-4.1-nano": {"input": 0.10,  "output": 0.40},
    "gpt-4.1-mini": {"input": 0.40,  "output": 1.60},
    "gpt-4.1":      {"input": 2.00,  "output": 8.00},
}

# Response style presets — hide raw parameters behind friendly labels
STYLE_PRESETS = {
    "🎯 Deterministic": {"temperature": 0.2, "top_p": 1.0,  "desc": "Consistent, low-variance answers"},
    "⚖️ Balanced":      {"temperature": 0.7, "top_p": 1.0,  "desc": "Creative yet coherent — default"},
    "🎨 Creative":      {"temperature": 1.1, "top_p": 0.95, "desc": "Expressive, more varied responses"},
    "⚙️ Custom":        {"temperature": 0.7, "top_p": 1.0,  "desc": "Set your own temperature and top-p"},
}

_MODEL_ICON_MAP = {
    "gpt-4o-mini":  "⚡",
    "gpt-4o":       "🧠",
    "gpt-4.1-nano": "🏎️",
    "gpt-4.1-mini": "⚖️",
    "gpt-4.1":      "💎",
}

_MODEL_SUBTITLE_MAP = {
    "gpt-4o-mini":  "Fast · $0.15/M in · $0.60/M out",
    "gpt-4o":       "Powerful · $2.50/M in · $10/M out",
    "gpt-4.1-nano": "Fastest · $0.10/M in · $0.40/M out",
    "gpt-4.1-mini": "Balanced · $0.40/M in · $1.60/M out",
    "gpt-4.1":      "Best · $2.00/M in · $8.00/M out",
}

_PERSONA_SUBTITLE_MAP = {
    "😐 Neutral":  "Professional and balanced feedback",
    "😤 Strict":   "Demanding — challenges every answer",
    "😊 Friendly": "Warm and encouraging atmosphere",
}

MODE_ICONS = {
    "General Q&A (Zero-Shot)": "💡",
    "Behavioral Interview (Few-Shot)": "🗣️",
    "Deep-Dive Questions (Chain-of-Thought)": "🔍",
    "Mock Interviewer (Role-Play)": "🎭",
    "Question Generator (Structured Output)": "📋",
}

MODE_SHORT = {
    "General Q&A (Zero-Shot)": "General Q&A",
    "Behavioral Interview (Few-Shot)": "Behavioral",
    "Deep-Dive Questions (Chain-of-Thought)": "Deep-Dive",
    "Mock Interviewer (Role-Play)": "Mock Interview",
    "Question Generator (Structured Output)": "Question Gen",
}

MODE_SUBTITLES = {
    "General Q&A (Zero-Shot)":                "Quick answers to any interview question",
    "Behavioral Interview (Few-Shot)":         "STAR method with guided examples",
    "Deep-Dive Questions (Chain-of-Thought)":  "Complex problems, step by step",
    "Mock Interviewer (Role-Play)":            "Simulate a real interview with AI",
    "Question Generator (Structured Output)":  "Generate question banks by topic",
}

MODE_PLACEHOLDERS = {
    "General Q&A (Zero-Shot)": "Ask any interview question, e.g. 'What is polymorphism?'",
    "Behavioral Interview (Few-Shot)": "Enter a behavioral question or paste your draft STAR answer...",
    "Deep-Dive Questions (Chain-of-Thought)": "Ask a complex question, e.g. 'Design a URL shortener'",
    "Mock Interviewer (Role-Play)": "Say 'Hi' to start the mock interview...",
    "Question Generator (Structured Output)": "Enter a topic, e.g. 'Python', 'System Design', 'Leadership'",
}

CTA_LABELS = {
    "General Q&A (Zero-Shot)":             "▶  Ask First Question",
    "Behavioral Interview (Few-Shot)":     "▶  Start Behavioral Practice",
    "Deep-Dive Questions (Chain-of-Thought)": "▶  Start Deep-Dive Session",
    "Mock Interviewer (Role-Play)":        "▶  Start Mock Interview",
    "Question Generator (Structured Output)": "▶  Generate First Question Set",
}

# Suggestion cards with subtext — replaces the plain suggestion list
SUGGESTIONS = {
    "General Q&A (Zero-Shot)": [
        {"text": "What are the SOLID principles?",          "sub": "OOP design · Fundamentals"},
        {"text": "Explain REST vs GraphQL",                 "sub": "API design · Architecture"},
        {"text": "How does garbage collection work?",       "sub": "Memory management · Internals"},
    ],
    "Behavioral Interview (Few-Shot)": [
        {"text": "Tell me about a time you dealt with a tight deadline",  "sub": "Time management · STAR method"},
        {"text": "Describe learning something new quickly",              "sub": "Adaptability · Growth mindset"},
        {"text": "Give an example of disagreeing with your manager",     "sub": "Conflict resolution · Communication"},
    ],
    "Deep-Dive Questions (Chain-of-Thought)": [
        {"text": "Design a URL shortening service",              "sub": "System design · Medium difficulty"},
        {"text": "How would you build a real-time chat app?",    "sub": "Architecture · Distributed systems"},
        {"text": "How does a database index work internally?",   "sub": "DB internals · Performance"},
    ],
    "Mock Interviewer (Role-Play)": [
        {"text": "Hi, I'm ready for my interview!",       "sub": "Start the simulation"},
        {"text": "I'd like to practice for a senior role","sub": "Senior-level questions"},
        {"text": "Let's start with technical questions",  "sub": "Technical focus track"},
    ],
    "Question Generator (Structured Output)": [
        {"text": "Python and data structures",         "sub": "Easy → Hard · 6+ questions"},
        {"text": "System design and scalability",      "sub": "Architecture & distributed systems"},
        {"text": "Leadership and team management",     "sub": "Behavioral & leadership track"},
    ],
}


MAX_JD_LENGTH = 3000

# Interviewer persona modifiers — appended to Mock Interviewer system prompt
PERSONA_MODIFIERS = {
    "😐 Neutral": "",
    "😤 Strict": (
        "\n\nPERSONA: You are a particularly STRICT and demanding interviewer. "
        "Challenge every answer. Probe for weaknesses, push back on vague responses, "
        "and maintain very high expectations. Ask tough follow-up questions. "
        "Be respectful but unrelenting — give credit only when the answer is genuinely strong."
    ),
    "😊 Friendly": (
        "\n\nPERSONA: You are a particularly WARM and FRIENDLY interviewer. "
        "Be encouraging and supportive. Celebrate good answers enthusiastically. "
        "Offer gentle hints when the candidate struggles. Create a relaxed, conversational "
        "atmosphere while still conducting a thorough and fair interview."
    ),
}


def _temp_label(t: float) -> str:
    if t <= 0.2:   return "🎯 Deterministic — very consistent, low variance"
    elif t <= 0.5: return "⚖️ Focused — reliable with some variation"
    elif t <= 0.8: return "✨ Balanced — creative yet coherent"
    elif t <= 1.1: return "🎨 Creative — expressive, occasionally surprising"
    else:          return "🔥 Experimental — highly varied, may go off-script"


def _top_p_label(p: float) -> str:
    if p <= 0.5:   return "🎯 Narrow — very focused vocabulary"
    elif p <= 0.8: return "⚖️ Moderate — balanced word choice"
    else:          return "🌐 Wide — full vocabulary range"


def _tokens_label(n: int) -> str:
    if n <= 300:    return "📝 Short response (~225 words)"
    elif n <= 700:  return "📄 Medium response (~525 words)"
    elif n <= 1200: return "📃 Detailed response (~900 words)"
    else:           return "📚 Comprehensive (~1500+ words)"


def _freq_label(f: float) -> str:
    if f <= 0.3:   return "🔄 Off — natural word frequency"
    elif f <= 0.8: return "⚖️ Light — slight repetition reduction"
    elif f <= 1.4: return "🔁 Moderate — reduces repeated phrases"
    else:          return "🚫 Strong — actively avoids repetition"


def _presence_label(p: float) -> str:
    if p <= 0.3:   return "📌 Off — stays on topic"
    elif p <= 0.8: return "⚖️ Light — mild topic diversity"
    elif p <= 1.4: return "🌿 Moderate — encourages new topics"
    else:          return "🌐 Strong — actively introduces new ideas"


_MODE_SUGGESTION_CONTEXT = {
    "General Q&A (Zero-Shot)":             "concise interview questions about concepts and technical skills",
    "Behavioral Interview (Few-Shot)":     "behavioral/situational questions using the STAR method",
    "Deep-Dive Questions (Chain-of-Thought)": "complex problems requiring step-by-step analysis",
    "Mock Interviewer (Role-Play)":        "opening lines to kick off a mock interview session",
    "Question Generator (Structured Output)": "topics or skill areas to generate a question bank from",
}


@st.cache_data(show_spinner=False, ttl=3600)
def _fetch_suggestions(role: str, mode: str, _api_key: str) -> list[dict]:
    """Generate 3 role-specific suggestion cards. Cached per (role, mode) pair."""
    context = _MODE_SUGGESTION_CONTEXT.get(mode, "interview practice prompts")
    try:
        _client = OpenAI(api_key=_api_key)
        response = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": (
                    f'Generate exactly 3 {context} for a "{role}" candidate. '
                    f'Return JSON: {{"suggestions": ['
                    f'{{"text": "<prompt, max 65 chars>", "sub": "<topic · difficulty, max 35 chars>"}}'
                    f', ...]}}. '
                    f'Make them specific to the {role} role. Return only valid JSON.'
                ),
            }],
            temperature=0.7,
            max_tokens=350,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        suggestions = data.get("suggestions", [])
        if len(suggestions) >= 3 and all("text" in s and "sub" in s for s in suggestions):
            return suggestions[:3]
    except Exception:
        pass
    # Fallback to static suggestions for this mode
    return SUGGESTIONS.get(mode, [])


st.set_page_config(page_title="Interview Practice", page_icon="💼", layout="wide")

# --- Fluid Dropdown Component ---
_fluid_dropdown = components.declare_component(
    "fluid_dropdown",
    path=str(Path(__file__).parent / "components" / "fluid_dropdown"),
)

def fluid_dropdown(options: list, value: str, key: str = None) -> str:
    """Render the fluid dropdown; returns the selected option value."""
    result = _fluid_dropdown(options=options, value=value, key=key, default=value)
    return result if result is not None else value

def inject_futuristic_theme() -> None:
    """
    Premium AI SaaS aesthetic — Zinc 950 base (#09090b), single purple
    ambient glow, frosted glass cards, Linear/Vercel-style sidebar.
    Injected via components.html JS so the <style> tag lands in <head>
    last and beats Streamlit's emotion CSS-in-JS injections.
    """
    _THEME_OPTS = {
        "theme.base":                     "dark",
        "theme.backgroundColor":          "#09090b",
        "theme.secondaryBackgroundColor": "#09090b",
        "theme.textColor":                "rgba(255,255,255,0.88)",
        "theme.primaryColor":             "#7c3aed",
    }
    for key, val in _THEME_OPTS.items():
        try:
            st._config.set_option(key, val)
        except Exception:
            pass

    _CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Base: Zinc 950 ──────────────────────────────────────────────────── */
html, body {
    background-color: #09090b !important;
}
body, .stApp, [class*="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stBottom"],
[data-testid="stAppViewContainer"] > section > div[class*="block-container"],
div[class*="block-container"],
div[class*="appview-container"],
div[class*="main"],
section[class*="main"],
.main, .block-container {
    background: transparent !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    border: none !important;
}

/* ── Ambient glow div (injected via JS) ──────────────────────────────── */
.ambient-glow {
    position: fixed !important;
    top: 40% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    width: 70vw !important;
    height: 50vh !important;
    background: radial-gradient(ellipse, rgba(124, 58, 237, 0.15) 0%, transparent 60%) !important;
    filter: blur(120px) !important;
    z-index: -1 !important;
    pointer-events: none !important;
}

/* ── Global text ─────────────────────────────────────────────────────── */
body, [data-testid="stAppViewContainer"],
div[class*="st-"], p, li, label, caption {
    color: rgba(255, 255, 255, 0.85) !important;
}
body, p, li, label, caption {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
h1 { font-weight: 800 !important; letter-spacing: -0.04em !important; color: rgba(255,255,255,0.96) !important; }
h2, h3, h4, h5, h6 { font-weight: 700 !important; letter-spacing: -0.02em !important; color: rgba(255,255,255,0.92) !important; }

/* ── Sidebar: flat Zinc 950, thin separator ──────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background: #09090b !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
}

/* ── All buttons: frosted glass base ─────────────────────────────────── */
div.stButton > button,
[data-testid="baseButton-secondary"] {
    background: rgba(24, 24, 27, 0.65) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
div.stButton > button:hover,
[data-testid="baseButton-secondary"]:hover {
    background: rgba(39, 39, 42, 0.8) !important;
    border-color: rgba(124, 58, 237, 0.4) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}

/* ── Primary CTA: tactile gradient ──────────────────────────────────── */
[data-testid="baseButton-primary"],
div.stButton > button[kind="primary"],
.cta-wrap .stButton > button,
.cta-wrap [data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, #8b5cf6 0%, #6d28d9 100%) !important;
    border: none !important;
    color: #fff !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 4px 12px rgba(109, 40, 217, 0.4) !important;
    animation: cta-pulse 2.8s ease-in-out infinite !important;
}
.cta-wrap .stButton > button:hover,
.cta-wrap [data-testid="baseButton-primary"]:hover {
    background: linear-gradient(180deg, #9d6ef8 0%, #7c3aed 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.25), 0 8px 24px rgba(109, 40, 217, 0.55) !important;
}

/* ── Command Center (chat input) ─────────────────────────────────────── */
/* Outer styled shell */
[data-testid="stChatInput"] > div {
    background: rgba(24, 24, 27, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #7c3aed !important;
    box-shadow: 0 0 0 1px #7c3aed, 0 8px 32px rgba(124, 58, 237, 0.25) !important;
}
/* Nuke ALL descendant backgrounds at any nesting depth */
[data-testid="stChatInput"] * {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
[data-testid="stChatInput"] textarea {
    caret-color: #a5b4fc !important;
    color: rgba(255, 255, 255, 0.9) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(255, 255, 255, 0.28) !important;
}

/* ── Sidebar iframe (fluid dropdown) ─────────────────────────────────── */
[data-testid="stSidebar"] iframe { border: none !important; }

/* ── Sidebar expander labels ─────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary div[class*="st-"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: rgba(255, 255, 255, 0.65) !important;
    opacity: 1 !important;
    margin: 0 !important;
}

/* ── Sidebar text input ──────────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] input[class*="st-"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.10) !important;
    border-radius: 12px !important;
    color: rgba(255, 255, 255, 0.88) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    box-shadow: none !important;
    transition: border-color 0.15s, background 0.15s !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input:focus {
    border-color: #7c3aed !important;
    background: rgba(255, 255, 255, 0.06) !important;
    box-shadow: 0 0 0 1px rgba(124,58,237,0.35) !important;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input::placeholder {
    color: rgba(255, 255, 255, 0.28) !important;
}

/* ── Captions ────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"],
[data-testid="stCaption"],
small {
    background: transparent !important;
    color: #a1a1aa !important;
    font-size: 0.85em !important;
}

/* ── Sidebar labels ──────────────────────────────────────────────────── */
.sidebar-label {
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    opacity: 0.35 !important; margin: 0 0 6px 2px !important;
    padding: 0 !important; line-height: 1 !important;
}
.context-badge {
    display: inline-block !important; padding: 5px 14px !important;
    border-radius: 20px !important; background: rgba(124,58,237,0.12) !important;
    border: 1px solid rgba(124,58,237,0.3) !important; color: #a5b4fc !important;
    font-size: 0.82em !important; font-weight: 500 !important;
    letter-spacing: 0.04em !important; margin-top: 2px !important;
}
.q-counter {
    display: inline-block !important; padding: 3px 12px !important;
    border-radius: 12px !important; background: rgba(124,58,237,0.15) !important;
    color: #a5b4fc !important; font-size: 0.55em !important;
    font-weight: 600 !important; vertical-align: middle !important;
    margin-left: 14px !important; letter-spacing: 0.08em !important;
}

/* ── Welcome card: frosted glass ─────────────────────────────────────── */
.welcome-box {
    position: relative !important;
    background: rgba(24, 24, 27, 0.65) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04) !important;
    padding: 40px 40px 36px !important;
    border-radius: 18px !important;
    margin-bottom: 20px !important;
    animation: slide-up-fade 0.55s cubic-bezier(0.16,1,0.3,1) both !important;
}
.welcome-steps {
    display: flex !important; justify-content: center !important;
    gap: 10px !important; flex-wrap: wrap !important; margin-top: 18px !important;
}
.welcome-step {
    display: flex !important; align-items: center !important; gap: 8px !important;
    padding: 8px 14px !important; border-radius: 10px !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    font-size: 0.84em !important; font-weight: 500 !important;
    color: rgba(255,255,255,0.70) !important;
}
.step-num {
    display: inline-flex !important; align-items: center !important;
    justify-content: center !important; width: 22px !important; height: 22px !important;
    border-radius: 50% !important;
    background: linear-gradient(135deg, #4338ca, #7c3aed) !important;
    color: white !important; font-size: 0.75em !important;
    font-weight: 700 !important; flex-shrink: 0 !important;
}

/* ── Suggestion buttons: frosted glass, purple hover ─────────────────── */
.suggestion-btn button {
    white-space: normal !important; word-break: break-word !important;
    width: 100% !important;
    height: auto !important; text-align: left !important;
    padding: 16px 18px !important; line-height: 1.5 !important;
    border-radius: 12px !important; font-size: 0.88em !important; font-weight: 500 !important;
    background: rgba(24, 24, 27, 0.65) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    color: rgba(255, 255, 255, 0.85) !important;
    transition: all 0.2s ease !important;
}
.suggestion-btn button:hover {
    transform: translateY(-2px) !important;
    border-color: rgba(124, 58, 237, 0.4) !important;
    background: rgba(39, 39, 42, 0.8) !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.4) !important;
}
.suggestion-btn .stButton > button,
.suggestion-btn [data-testid^="baseButton"] {
    min-height: 96px !important;
    align-items: flex-start !important;
}
/* Collapse gap in suggestion columns so subtext hugs the button */
[data-testid="column"]:has(.suggestion-btn) [data-testid="stVerticalBlock"] {
    gap: 0 !important;
}
/* Subtext hugs the button */
.suggestion-sub {
    display: block !important;
    color: #71717a !important;
    font-size: 0.75rem !important;
    margin-top: 4px !important;
    padding: 0 2px !important;
    letter-spacing: 0.01em !important;
}

/* ── Misc ────────────────────────────────────────────────────────────── */
.stat-card {
    background: linear-gradient(135deg,#4338ca 0%,#7c3aed 100%) !important;
    padding: 16px 20px !important; border-radius: 12px !important;
    color: white !important; text-align: center !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
.topics-label {
    font-size: 0.75rem !important; font-weight: 600 !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    color: #71717a !important; margin: 24px 0 1rem 0 !important;
    padding: 0 !important;
}

/* ── Premium Welcome Card ────────────────────────────────────────────── */
.welcome-card-premium {
    background: linear-gradient(180deg, rgba(24,24,27,0.7) 0%, rgba(9,9,11,0.8) 100%) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-top: 1px solid rgba(168,85,247,0.4) !important;
    border-radius: 16px !important; padding: 2.5rem !important;
    text-align: center !important;
    box-shadow: 0 20px 40px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.05) !important;
    backdrop-filter: blur(20px) !important; margin-bottom: 2rem !important;
}
.welcome-header {
    display: flex !important; justify-content: center !important;
    align-items: center !important; gap: 12px !important; margin-bottom: 10px !important;
}
.welcome-icon { color: #a855f7 !important; filter: drop-shadow(0 0 8px rgba(168,85,247,0.5)) !important; }
.welcome-title { font-size: 1.8rem !important; font-weight: 700 !important; color: #ffffff !important; margin: 0 !important; }
.title-muted { color: #71717a !important; font-weight: 500 !important; font-size: 1.4rem !important; }
.welcome-subtitle { color: #a1a1aa !important; font-size: 1rem !important; margin-bottom: 2rem !important; }
.role-highlight { color: #e9d5ff !important; font-weight: 600 !important; border-bottom: 1px dashed rgba(168,85,247,0.5) !important; }
.steps-row {
    display: flex !important; justify-content: center !important;
    gap: 16px !important; flex-wrap: wrap !important;
}
.step-pill {
    display: flex !important; align-items: center !important; gap: 10px !important;
    background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.05) !important;
    padding: 8px 18px 8px 8px !important; border-radius: 99px !important;
    transition: all 0.2s ease !important; cursor: default !important;
}
.step-pill:hover {
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(168,85,247,0.4) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}
.step-num-badge {
    display: flex !important; justify-content: center !important; align-items: center !important;
    width: 26px !important; height: 26px !important;
    background: linear-gradient(135deg, #a855f7, #6366f1) !important;
    border-radius: 50% !important; color: white !important;
    font-size: 0.8rem !important; font-weight: bold !important;
    box-shadow: 0 0 10px rgba(168,85,247,0.4) !important; flex-shrink: 0 !important;
}
.step-text { color: #d4d4d8 !important; font-size: 0.9rem !important; font-weight: 500 !important; }

/* ── Hero Section ────────────────────────────────────────────────────── */
.hero-container {
    display: flex !important; flex-direction: column !important;
    align-items: center !important; text-align: center !important;
    margin-bottom: 2.5rem !important; margin-top: 1rem !important;
    animation: fade-in-down 0.6s ease-out !important;
}
.hero-badge {
    display: inline-flex !important; align-items: center !important;
    gap: 8px !important; padding: 6px 16px !important;
    border-radius: 999px !important;
    background: rgba(124, 58, 237, 0.1) !important;
    border: 1px solid rgba(124, 58, 237, 0.3) !important;
    color: #d8b4fe !important; font-size: 0.75rem !important;
    font-weight: 600 !important; letter-spacing: 0.05em !important;
    text-transform: uppercase !important; margin-bottom: 1rem !important;
    box-shadow: 0 0 12px rgba(124, 58, 237, 0.15) !important;
}
.hero-badge-dot {
    width: 6px !important; height: 6px !important;
    background-color: #a855f7 !important; border-radius: 50% !important;
    box-shadow: 0 0 8px #a855f7 !important;
    animation: pulse-dot 2s infinite !important;
    display: inline-block !important; flex-shrink: 0 !important;
}
.hero-title {
    font-size: 3.2rem !important; font-weight: 800 !important;
    letter-spacing: -0.03em !important; color: #ffffff !important;
    margin: 0 !important; line-height: 1.1 !important;
}
.hero-highlight {
    background: linear-gradient(135deg, #a855f7 0%, #6366f1 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important; color: transparent !important;
}
.hero-subtitle {
    color: #a1a1aa !important; font-size: 1.1rem !important;
    margin-top: 1rem !important; max-width: 500px !important;
    font-weight: 400 !important; line-height: 1.5 !important;
}

/* ── Voice input ─────────────────────────────────────────────────────── */
/* Center only the column that holds the mic iframe */
div[data-testid="column"]:has(iframe[title*="streamlit_mic_recorder"]) {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    margin-bottom: 10px !important;
}
/* Tight transparent wrap — hides the double-box effect */
iframe[title="streamlit_mic_recorder"],
iframe[title*="streamlit_mic_recorder"],
iframe[title*="speech_to_text"] {
    width: 160px !important;
    height: 50px !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

/* ── AI Thinking Soundwave ───────────────────────────────────────────── */
.ai-thinking-container {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    padding: 16px 24px !important;
    background: rgba(24, 24, 27, 0.4) !important;
    border: 1px solid rgba(124, 58, 237, 0.2) !important;
    border-radius: 12px !important;
    width: fit-content !important;
    margin-bottom: 1.5rem !important;
    backdrop-filter: blur(12px) !important;
}
.ai-thinking-text {
    color: #a855f7 !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
}
.soundwave {
    display: flex !important;
    align-items: center !important;
    gap: 4px !important;
    height: 20px !important;
}
.soundwave .bar {
    width: 4px !important;
    background: #a855f7 !important;
    border-radius: 4px !important;
    animation: wave 1s ease-in-out infinite !important;
}
.soundwave .bar:nth-child(1) { height: 8px !important;  animation-delay: -0.4s !important; }
.soundwave .bar:nth-child(2) { height: 16px !important; animation-delay: -0.2s !important; }
.soundwave .bar:nth-child(3) { height: 12px !important; animation-delay:  0.0s !important; }
@keyframes wave {
    0%, 100% { transform: scaleY(0.5); opacity: 0.5; }
    50%       { transform: scaleY(1);   opacity: 1;   }
}

/* ── Keyframes ───────────────────────────────────────────────────────── */
@keyframes fade-in-down {
    0%   { opacity: 0; transform: translateY(-15px); }
    100% { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.4; transform: scale(0.8); }
}
@keyframes slide-up-fade {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes cta-pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(124,58,237,0.40), 0 4px 16px rgba(67,56,202,0.35); }
    50%       { box-shadow: 0 0 36px rgba(124,58,237,0.70), 0 6px 28px rgba(124,58,237,0.55); }
}
@property --beam-angle { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes border-beam-spin { to { --beam-angle: 360deg; } }

/* Staggered suggestion entry */
.suggestion-btn { animation: slide-up-fade 0.45s cubic-bezier(0.16,1,0.3,1) backwards !important; }
.suggestion-btn-0 { animation-delay: 0.08s !important; }
.suggestion-btn-1 { animation-delay: 0.16s !important; }
.suggestion-btn-2 { animation-delay: 0.24s !important; }

/* Border beam on welcome card */
.welcome-box::after {
    content: '' !important; position: absolute !important; inset: 0 !important;
    border-radius: 18px !important; padding: 1px !important;
    background: conic-gradient(from var(--beam-angle), transparent 0deg, transparent 310deg,
        rgba(124,58,237,0.35) 338deg, rgba(165,180,252,0.85) 350deg,
        rgba(124,58,237,0.35) 360deg) !important;
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
    -webkit-mask-composite: destination-out !important;
    mask-composite: exclude !important;
    animation: border-beam-spin 5s linear infinite !important;
    pointer-events: none !important; z-index: 0 !important;
}

/* ── Phase 3: Premium Chat Bubbles ─────────────────────────────────────── */

/* Base chat container */
[data-testid="stChatMessage"] {
    padding: 1.5rem !important;
    margin-bottom: 1.5rem !important;
    border-radius: 12px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
}

/* User message — subtle, muted, whispering */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
[data-testid="stChatMessage"]:nth-child(odd) {
    background: rgba(24, 24, 27, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
    box-shadow: none !important;
}

/* Assistant message — authoritative, elevated, purple tint */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
[data-testid="stChatMessage"]:nth-child(even) {
    background: linear-gradient(145deg, rgba(24, 24, 27, 0.8), rgba(18, 18, 20, 0.9)) !important;
    border: 1px solid rgba(124, 58, 237, 0.15) !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
}

/* Typography & readability */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    color: rgba(255, 255, 255, 0.9) !important;
    line-height: 1.65 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.01em !important;
}

/* Avatar — modern square app-icon style */
[data-testid="stChatMessage"] [data-testid="stChatAvatar"] {
    border-radius: 8px !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}
"""

    _css_js = json.dumps(_CSS)

    components.html(
        f"""
<script>
(function () {{
  var pd = window.parent.document;

  // ── Inject ambient glow div (once) ────────────────────────────────────
  if (!pd.getElementById('ambient-glow')) {{
    var g = pd.createElement('div');
    g.id        = 'ambient-glow';
    g.className = 'ambient-glow';
    pd.body.prepend(g);
  }}

  // ── Stylesheet: appended last so it beats emotion CSS injections ──────
  var existing = pd.getElementById('ft-style');
  if (existing) existing.remove();
  var s = pd.createElement('style');
  s.id = 'ft-style';
  s.textContent = {_css_js};
  pd.head.appendChild(s);

  // ── MutationObserver: keep ft-style last whenever emotion adds a tag ──
  if (!pd._ftObserver) {{
    pd._ftObserver = new MutationObserver(function () {{
      var ft = pd.getElementById('ft-style');
      if (ft && pd.head.lastElementChild !== ft) pd.head.appendChild(ft);
    }});
    pd._ftObserver.observe(pd.head, {{ childList: true }});
  }}
}})();
</script>
""",
        height=0,
    )


# Apply the futuristic theme immediately after page config
inject_futuristic_theme()


st.sidebar.markdown("## Settings")

st.sidebar.markdown('<p class="sidebar-label">Practice Mode</p>', unsafe_allow_html=True)

_MODE_OPTIONS = [
    {
        "value":    k,
        "icon":     MODE_ICONS.get(k, ""),
        "label":    MODE_SHORT.get(k, k),
        "tag":      k[k.index("(")+1 : k.rindex(")")] if "(" in k else "",
        "subtitle": MODE_SUBTITLES.get(k, ""),
    }
    for k in PROMPTS.keys()
]

if "mode" not in st.session_state:
    st.session_state.mode = list(PROMPTS.keys())[0]

with st.sidebar:
    _selected_mode = fluid_dropdown(
        options=_MODE_OPTIONS,
        value=st.session_state.mode,
        key="mode_dropdown",
    )
if _selected_mode != st.session_state.mode:
    st.session_state.mode = _selected_mode
mode = st.session_state.mode

# ── Model ─────────────────────────────────────────────────────
_MODEL_OPTIONS = [
    {
        "value":    m,
        "icon":     _MODEL_ICON_MAP.get(m, "🤖"),
        "label":    MODEL_LABELS[m],
        "tag":      "",
        "subtitle": _MODEL_SUBTITLE_MAP.get(m, ""),
    }
    for m in MODEL_OPTIONS
]
st.sidebar.markdown('<p class="sidebar-label">Model</p>', unsafe_allow_html=True)
if "model" not in st.session_state:
    st.session_state.model = MODEL_OPTIONS[0]
with st.sidebar:
    _selected_model = fluid_dropdown(options=_MODEL_OPTIONS, value=st.session_state.model, key="model_dropdown")
if _selected_model != st.session_state.model:
    st.session_state.model = _selected_model
model = st.session_state.model

# ── Job Role ──────────────────────────────────────────────────
st.sidebar.markdown('<p class="sidebar-label">Job Role</p>', unsafe_allow_html=True)
job_role = st.sidebar.text_input(
    "Job Role",
    value="Software Engineer",
    placeholder="e.g. Software Engineer, Product Manager…",
    label_visibility="collapsed",
)

# Security: validate job role (injected into every system prompt)
if len(job_role) > MAX_ROLE_LENGTH:
    st.sidebar.error(f"Job role too long (max {MAX_ROLE_LENGTH} chars).")
    job_role = job_role[:MAX_ROLE_LENGTH]
if _is_injection(job_role):
    st.sidebar.error("⚠️ Job role contains disallowed content. Please enter a real job title.")
    job_role = "Software Engineer"

# ── Interviewer Persona (Mock Interviewer mode only) ──────────
if mode == "Mock Interviewer (Role-Play)":
    _PERSONA_OPTIONS = [
        {
            "value":    k,
            "icon":     k.split()[0],
            "label":    " ".join(k.split()[1:]),
            "tag":      "",
            "subtitle": _PERSONA_SUBTITLE_MAP.get(k, ""),
        }
        for k in PERSONA_MODIFIERS.keys()
    ]
    st.sidebar.markdown('<p class="sidebar-label">Interviewer Persona</p>', unsafe_allow_html=True)
    if "persona" not in st.session_state:
        st.session_state.persona = "😐 Neutral"
    with st.sidebar:
        _selected_persona = fluid_dropdown(options=_PERSONA_OPTIONS, value=st.session_state.persona, key="persona_dropdown")
    if _selected_persona != st.session_state.persona:
        st.session_state.persona = _selected_persona
    persona = st.session_state.persona
else:
    persona = "😐 Neutral"

with st.sidebar.expander("Job Description (optional)", expanded=False):
    job_description = st.text_area(
        "Paste the job posting",
        value="",
        height=150,
        max_chars=MAX_JD_LENGTH,
        placeholder="e.g. Senior Software Engineer at Acme Corp...\n\nResponsibilities:\n- Build scalable APIs\n- Lead code reviews...",
        help="Paste the actual job description to get tailored questions and advice for that specific role.",
        label_visibility="collapsed",
    )
    if job_description:
        st.caption(f"{len(job_description)} / {MAX_JD_LENGTH} chars")
        if _is_injection(job_description):
            st.error("⚠️ Job description contains disallowed content.")
            job_description = ""

with st.sidebar.expander("About this mode", expanded=False):
    st.markdown(PROMPTS[mode]["description"])

# ── Response Style ────────────────────────────────────────────
st.sidebar.markdown("---")
_STYLE_OPTIONS = [
    {
        "value":    k,
        "icon":     k.split()[0],
        "label":    " ".join(k.split()[1:]),
        "tag":      "",
        "subtitle": STYLE_PRESETS[k]["desc"],
    }
    for k in STYLE_PRESETS.keys()
]
st.sidebar.markdown('<p class="sidebar-label">Response Style</p>', unsafe_allow_html=True)
if "style_preset" not in st.session_state:
    st.session_state.style_preset = "⚖️ Balanced"
with st.sidebar:
    _selected_style = fluid_dropdown(options=_STYLE_OPTIONS, value=st.session_state.style_preset, key="style_dropdown")
if _selected_style != st.session_state.style_preset:
    st.session_state.style_preset = _selected_style
style_preset = st.session_state.style_preset

is_custom = style_preset == "⚙️ Custom"
_preset = STYLE_PRESETS[style_preset]

with st.sidebar.expander("Advanced Settings", expanded=False):
    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0,
        max_value=1.5,
        value=_preset["temperature"],
        step=0.1,
        disabled=not is_custom,
        key=f"temp_{style_preset}",
        help="Controls randomness. OpenAI recommends tuning Temperature OR Top-p, not both.",
    )
    st.caption(_temp_label(temperature))

    top_p = st.slider(
        "🎯 Top-p",
        min_value=0.1,
        max_value=1.0,
        value=_preset["top_p"],
        step=0.05,
        disabled=not is_custom,
        key=f"top_p_{style_preset}",
        help="Nucleus sampling threshold. Leave at 1.0 if adjusting Temperature.",
    )
    st.caption(_top_p_label(top_p))

    max_tokens = st.slider(
        "📏 Max Tokens",
        min_value=100,
        max_value=2000,
        value=800,
        step=100,
        help="Maximum tokens in the response. 1 token ≈ 0.75 words.",
    )
    st.caption(_tokens_label(max_tokens))

    frequency_penalty = st.slider(
        "🔁 Frequency Penalty",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.1,
        help=(
            "Reduces the likelihood of repeating the same words/phrases. "
            "Higher values discourage word-level repetition across the response."
        ),
    )
    st.caption(_freq_label(frequency_penalty))

    presence_penalty = st.slider(
        "🆕 Presence Penalty",
        min_value=0.0,
        max_value=2.0,
        value=0.0,
        step=0.1,
        help=(
            "Encourages the model to introduce new topics and concepts. "
            "Higher values make the model more likely to explore different angles."
        ),
    )
    st.caption(_presence_label(presence_penalty))

st.sidebar.markdown("---")

if st.sidebar.button("🗑️ Clear Chat", width="stretch"):
    st.session_state.messages = []
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0
    st.session_state.interviewer_avatar_url = None
    st.session_state.interviewer_avatar_role = None
    st.rerun()

# --- API Key Validation ---
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key or api_key == "your-key-here":
    st.error(
        "OpenAI API key not found. Please create a `.env` file with your key:\n\n"
        "```\nOPENAI_API_KEY=sk-...\n```"
    )
    st.stop()

client = OpenAI(api_key=api_key)

# --- Chat History & Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_mode" not in st.session_state:
    st.session_state.current_mode = mode
if "current_role" not in st.session_state:
    st.session_state.current_role = job_role
if "current_model" not in st.session_state:
    st.session_state.current_model = model
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0
if "pending_suggestion" not in st.session_state:
    st.session_state.pending_suggestion = None
if "last_mic_id" not in st.session_state:
    st.session_state.last_mic_id = None
if "current_persona" not in st.session_state:
    st.session_state.current_persona = persona
if "interviewer_avatar_url" not in st.session_state:
    st.session_state.interviewer_avatar_url = None
if "interviewer_avatar_role" not in st.session_state:
    st.session_state.interviewer_avatar_role = None

# Reset chat when mode, role, or model changes
if (
    st.session_state.current_mode != mode
    or st.session_state.current_role != job_role
    or st.session_state.current_model != model
    or st.session_state.current_persona != persona
):
    st.session_state.messages = []
    st.session_state.total_input_tokens = 0
    st.session_state.total_output_tokens = 0
    st.session_state.interviewer_avatar_url = None
    st.session_state.interviewer_avatar_role = None
    st.session_state.current_mode = mode
    st.session_state.current_role = job_role
    st.session_state.current_model = model
    st.session_state.current_persona = persona

# --- Header ---
user_msgs = sum(1 for m in st.session_state.messages if m["role"] == "user")

col1, col2, col3 = st.columns([2, 5, 2])
with col2:
    if user_msgs > 0:
        st.markdown(
            f'<div class="hero-container">'
            f'<div class="hero-badge"><span class="hero-badge-dot"></span>AI-Powered Coaching</div>'
            f'<h1 class="hero-title">Interview <span class="hero-highlight">Companion</span>'
            f'<span class="q-counter">Question {user_msgs}</span></h1>'
            f'<p class="hero-subtitle">Master your next role with dynamic, real-time feedback.</p>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="hero-container">'
            '<div class="hero-badge"><span class="hero-badge-dot"></span>AI-Powered Coaching</div>'
            '<h1 class="hero-title">Interview <span class="hero-highlight">Companion</span></h1>'
            '<p class="hero-subtitle">Master your next role with dynamic, real-time feedback.</p>'
            '</div>',
            unsafe_allow_html=True,
        )

# --- Empty State: Welcome Box + CTA ---
if not st.session_state.messages:
    cta_label = CTA_LABELS.get(mode, "▶  Start Practice")

    # Build mode title: strip parenthetical tag for cleaner display
    _mode_short = mode.split("(")[0].strip()
    _mode_tag = f'({mode.split("(")[1]}' if "(" in mode else ""
    st.markdown(f"""
<div class="welcome-card-premium">
  <div class="welcome-header">
    <svg class="welcome-icon" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>
      <path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>
    </svg>
    <h2 class="welcome-title">{_mode_short} <span class="title-muted">{_mode_tag}</span></h2>
  </div>
  <p class="welcome-subtitle">Preparing for a <span class="role-highlight">{job_role}</span> role</p>
  <div class="steps-row">
    <div class="step-pill"><span class="step-num-badge">1</span><span class="step-text">Pick a mode &amp; role</span></div>
    <div class="step-pill"><span class="step-num-badge">2</span><span class="step-text">Click a suggestion</span></div>
    <div class="step-pill"><span class="step-num-badge">3</span><span class="step-text">Continue the chat</span></div>
  </div>
</div>
""", unsafe_allow_html=True)

    # --- Interviewer avatar (Mock Interviewer mode only) ---
    if mode == "Mock Interviewer (Role-Play)":
        needs_avatar = (
            st.session_state.interviewer_avatar_url is None
            or st.session_state.interviewer_avatar_role != job_role
        )
        if needs_avatar:
            with st.spinner("🎨 Generating your interviewer portrait..."):
                try:
                    img_resp = client.images.generate(
                        model="dall-e-3",
                        prompt=(
                            f"Professional corporate headshot photograph of a friendly senior "
                            f"{job_role} interviewer named Alex. Smart business casual attire "
                            f"appropriate for the industry, confident and approachable expression, "
                            f"soft neutral office bokeh background, photorealistic, high quality "
                            f"portrait photography. No text, no watermarks, no labels."
                        ),
                        size="1024x1024",
                        quality="standard",
                        n=1,
                    )
                    st.session_state.interviewer_avatar_url = img_resp.data[0].url
                    st.session_state.interviewer_avatar_role = job_role
                except Exception:
                    st.session_state.interviewer_avatar_url = None

        if st.session_state.interviewer_avatar_url:
            col_l, col_img, col_r = st.columns([1.5, 1, 1.5])
            with col_img:
                st.image(
                    st.session_state.interviewer_avatar_url,
                    caption=f"Alex — your {job_role} interviewer",
                    width="stretch",
                )
            st.markdown("<br>", unsafe_allow_html=True)

    # Fetch role-specific suggestions (cached — spinner only shows on first load for a new role)
    with st.spinner(f"✨ Personalising suggestions for **{job_role}**..."):
        active_suggestions = (
            _fetch_suggestions(job_role, mode, api_key)
            if len(job_role) >= 3
            else SUGGESTIONS.get(mode, [])
        )

    first_suggestion = active_suggestions[0]["text"] if active_suggestions else ""

    # Primary CTA
    col_l, col_cta, col_r = st.columns([1, 2, 1])
    with col_cta:
        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        if st.button(cta_label, width="stretch", type="primary", key="cta_btn"):
            st.session_state.pending_suggestion = first_suggestion
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<p class="topics-label">Choose a specific topic</p>', unsafe_allow_html=True)

    # Suggestion cards: 3 equal columns, all aligned in one row
    if len(active_suggestions) >= 3:
        cols = st.columns([1, 1, 1], gap="medium")
        for i in range(3):
            with cols[i]:
                s = active_suggestions[i]
                st.markdown(f'<div class="suggestion-btn suggestion-btn-{i}">', unsafe_allow_html=True)
                if st.button(s["text"], key=f"suggestion_{i}", width="stretch"):
                    st.session_state.pending_suggestion = s["text"]
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f'<span class="suggestion-sub">{s["sub"]}</span>', unsafe_allow_html=True)
    else:
        cols = st.columns(max(len(active_suggestions), 1), gap="medium")
        for i, s in enumerate(active_suggestions):
            with cols[i]:
                st.markdown(f'<div class="suggestion-btn suggestion-btn-{i}">', unsafe_allow_html=True)
                if st.button(s["text"], key=f"suggestion_{i}", width="stretch"):
                    st.session_state.pending_suggestion = s["text"]
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown(f'<span class="suggestion-sub">{s["sub"]}</span>', unsafe_allow_html=True)

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Stats in sidebar
if st.session_state.messages:
    costs = MODEL_COSTS[model]
    total_cost = (
        st.session_state.total_input_tokens / 1_000_000 * costs["input"]
        + st.session_state.total_output_tokens / 1_000_000 * costs["output"]
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### 📊 Session Stats")
    st.sidebar.metric("Questions Asked", user_msgs)
    st.sidebar.metric("Total Messages", len(st.session_state.messages))
    st.sidebar.metric(
        "Tokens Used",
        f"{st.session_state.total_input_tokens + st.session_state.total_output_tokens:,}",
        help=f"Input: {st.session_state.total_input_tokens:,} | Output: {st.session_state.total_output_tokens:,}",
    )
    st.sidebar.metric(
        "Est. Cost",
        f"${total_cost:.4f}",
        help="Estimated cost based on current OpenAI pricing. Prices may change.",
    )

# --- Voice Input ---
_, _mic_c, __ = st.columns([1, 1, 1])
with _mic_c:
    audio_data = mic_recorder(
        start_prompt="Tap to Speak",
        stop_prompt="⏹  Stop Recording",
        just_once=True,
        key="mic_recorder",
    )

voice_input = None
if audio_data and audio_data.get("id") != st.session_state.last_mic_id:
    st.session_state.last_mic_id = audio_data["id"]
    with st.spinner("🎙️ Transcribing…"):
        voice_input = _transcribe_audio(client, audio_data["bytes"])
    if voice_input:
        st.toast(f'Transcribed: "{voice_input[:80]}"')

# --- Text Input ---
placeholder = MODE_PLACEHOLDERS.get(mode, "Type your question or answer here...")
user_input = st.chat_input(placeholder)

# Handle suggestion / CTA button click
if st.session_state.pending_suggestion:
    user_input = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None

# Voice takes priority if both fire on the same rerun
if voice_input:
    user_input = voice_input

if user_input:
    # Security: input length limit
    if len(user_input) > MAX_INPUT_LENGTH:
        st.error(
            f"Input too long ({len(user_input)} characters). "
            f"Please keep it under {MAX_INPUT_LENGTH} characters."
        )
        st.stop()

    # Security: prompt injection detection
    if _is_injection(user_input):
        st.error(
            "⚠️ Your message contains disallowed content. "
            "Please keep your questions interview-related."
        )
        st.stop()

    # Add user message to history and display
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build messages for API call
    system_prompt = PROMPTS[mode]["system"].format(role=job_role)
    # Append persona modifier for Mock Interviewer mode
    system_prompt += PERSONA_MODIFIERS.get(persona, "")
    # Inject job description if provided
    if job_description.strip():
        system_prompt += (
            f"\n\nJOB DESCRIPTION FOR THIS SESSION:\n"
            f"The candidate is applying for the following position. Tailor all your "
            f"questions, feedback, and advice specifically to this role:\n\n{job_description}"
        )
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages:
        api_messages.append({"role": msg["role"], "content": msg["content"]})

    # Call OpenAI API
    with st.chat_message("assistant"):
        thinking_placeholder = st.empty()
        thinking_placeholder.markdown(
            '<div class="ai-thinking-container">'
            '<div class="soundwave">'
            '<div class="bar"></div><div class="bar"></div><div class="bar"></div>'
            '</div>'
            '<span class="ai-thinking-text">Thinking…</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        try:
            response = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
            )
            thinking_placeholder.empty()
            assistant_message = response.choices[0].message.content
            st.markdown(assistant_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_message}
            )
            # Track token usage for cost display
            if response.usage:
                st.session_state.total_input_tokens += response.usage.prompt_tokens
                st.session_state.total_output_tokens += response.usage.completion_tokens
        except Exception as e:
            thinking_placeholder.empty()
            st.error(f"Error calling OpenAI API: {e}")

# --- Typewriter placeholder for Command Bar ---
components.html("""
<script>
(function () {
  var PHRASES = [
    "Ask any interview question\u2026",
    "What are the SOLID principles?",
    "Design a URL shortening service\u2026",
    "Tell me about a time you led a project\u2026",
    "How does garbage collection work?",
    "Walk me through a system design\u2026",
  ];
  var pi = 0, ci = 0, deleting = false;

  function getTA() {
    return window.parent.document.querySelector(
      'div[data-testid="stChatInput"] textarea'
    );
  }

  function tick() {
    var el = getTA();
    if (!el) { setTimeout(tick, 500); return; }
    if (el === window.parent.document.activeElement) { setTimeout(tick, 300); return; }

    var phrase = PHRASES[pi];
    if (!deleting) {
      ci++;
      el.setAttribute("placeholder", phrase.slice(0, ci));
      if (ci >= phrase.length) { deleting = true; setTimeout(tick, 2200); }
      else { setTimeout(tick, 65); }
    } else {
      ci--;
      el.setAttribute("placeholder", phrase.slice(0, ci));
      if (ci <= 0) {
        deleting = false;
        pi = (pi + 1) % PHRASES.length;
        setTimeout(tick, 400);
      } else { setTimeout(tick, 32); }
    }
  }

  // Start once the textarea appears in the parent DOM
  var obs = new MutationObserver(function () {
    if (getTA()) { obs.disconnect(); tick(); }
  });
  obs.observe(window.parent.document.body, { childList: true, subtree: true });
  // Also try immediately in case it's already rendered
  if (getTA()) { obs.disconnect(); tick(); }
})();
</script>
""", height=0)
