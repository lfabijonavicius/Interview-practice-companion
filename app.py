import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import json

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

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    h1 { font-weight: 800 !important; letter-spacing: -0.5px !important; }
    h2, h3 { font-weight: 700 !important; }

    /* Compact context badge beneath the title */
    .context-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        background: rgba(102, 126, 234, 0.1);
        border: 1px solid rgba(102, 126, 234, 0.25);
        color: #667eea;
        font-size: 0.82em;
        font-weight: 500;
        letter-spacing: 0.3px;
        margin-top: 2px;
    }

    /* Question counter badge shown in the header during an active session */
    .q-counter {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 12px;
        background: rgba(102, 126, 234, 0.12);
        color: #667eea;
        font-size: 0.55em;
        font-weight: 600;
        vertical-align: middle;
        margin-left: 14px;
        letter-spacing: 0.5px;
    }

    /* Welcome / hero box — glassmorphism */
    .welcome-box {
        background: rgba(102, 126, 234, 0.07);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(102, 126, 234, 0.22);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1), 0 2px 8px rgba(0, 0, 0, 0.06);
        padding: 32px 28px 26px;
        border-radius: 18px;
        margin-bottom: 20px;
    }
    .welcome-steps {
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 18px;
    }
    .welcome-step {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        border-radius: 10px;
        background: rgba(102, 126, 234, 0.08);
        border: 1px solid rgba(102, 126, 234, 0.15);
        font-size: 0.84em;
        font-weight: 500;
    }
    .step-num {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: #667eea;
        color: white;
        font-size: 0.75em;
        font-weight: 700;
        flex-shrink: 0;
    }

    /* Suggestion chips — wrapping + hover lift */
    .suggestion-btn button {
        white-space: normal !important;
        word-break: break-word !important;
        height: auto !important;
        text-align: left !important;
        padding: 12px 16px !important;
        line-height: 1.4 !important;
        border-radius: 12px !important;
        font-size: 0.88em !important;
        font-weight: 500 !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease !important;
    }
    .suggestion-btn button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.28) !important;
        border-color: rgba(102, 126, 234, 0.5) !important;
    }

    /* Stat card */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .stat-card h3 { margin: 0; font-size: 1.8em; }
    .stat-card p  { margin: 4px 0 0 0; opacity: 0.85; font-size: 0.9em; }

    /* ── Sidebar section header label ───────────────────────── */
    .sidebar-label {
        font-size: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        opacity: 0.4 !important;
        margin: 0 0 6px 2px !important;
        padding: 0 !important;
        line-height: 1 !important;
    }

    /* Remove default iframe border for the fluid dropdown component */
    section[data-testid="stSidebar"] iframe {
        border: none !important;
    }

    /* Style sidebar text input to match the fluid dropdown white aesthetic */
    section[data-testid="stSidebar"] .stTextInput input {
        background: rgba(255, 255, 255, 0.92) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        border-radius: 12px !important;
        color: rgba(20, 20, 45, 0.85) !important;
        font-size: 12.5px !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.07) !important;
        transition: border-color 0.15s, background 0.15s, box-shadow 0.15s !important;
    }
    section[data-testid="stSidebar"] .stTextInput input:hover {
        border-color: rgba(102, 126, 234, 0.4) !important;
        background: #ffffff !important;
        box-shadow: 0 2px 10px rgba(102, 126, 234, 0.12) !important;
    }
    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: rgba(102, 126, 234, 0.55) !important;
        background: #ffffff !important;
        box-shadow: 0 0 0 1px rgba(102, 126, 234, 0.2), 0 4px 16px rgba(102, 126, 234, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.markdown("## ⚙️ Settings")

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

with st.sidebar.expander("📄 Job Description (optional)", expanded=False):
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

with st.sidebar.expander("ℹ️ About this mode", expanded=False):
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

with st.sidebar.expander("⚙️ Advanced Settings", expanded=False):
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
            f"# {MODE_ICONS.get(mode, '💼')} Interview Practice"
            f'<span class="q-counter">Question {user_msgs}</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"# {MODE_ICONS.get(mode, '💼')} Interview Practice")
    st.markdown(
        f'<div style="text-align:center; margin-bottom: 8px;">'
        f'<span class="context-badge">'
        f'{job_role} · {MODE_SHORT[mode]} · {MODEL_LABELS[model]}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

# --- Empty State: Welcome Box + CTA ---
if not st.session_state.messages:
    cta_label = CTA_LABELS.get(mode, "▶  Start Practice")

    st.markdown(f"""
<div class="welcome-box">
  <h3 style="margin: 0 0 4px 0; text-align: center;">
    {MODE_ICONS.get(mode, '💼')} {mode}
  </h3>
  <p style="opacity: 0.65; margin: 0; text-align: center; font-size: 0.92em;">
    Preparing for a <strong>{job_role}</strong> role
  </p>
  <div class="welcome-steps">
    <div class="welcome-step"><span class="step-num">1</span> Pick a mode &amp; role in the sidebar</div>
    <div class="welcome-step"><span class="step-num">2</span> Click a suggestion or type your own</div>
    <div class="welcome-step"><span class="step-num">3</span> Continue the conversation</div>
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
        if st.button(cta_label, width="stretch", type="primary", key="cta_btn"):
            st.session_state.pending_suggestion = first_suggestion

    st.markdown("##### Or choose a specific topic:")

    cols = st.columns(3)
    for i, suggestion in enumerate(active_suggestions):
        with cols[i]:
            st.markdown('<div class="suggestion-btn">', unsafe_allow_html=True)
            if st.button(suggestion["text"], key=f"suggestion_{i}", width="stretch"):
                st.session_state.pending_suggestion = suggestion["text"]
            st.markdown('</div>', unsafe_allow_html=True)
            st.caption(suggestion["sub"])

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

# --- User Input ---
placeholder = MODE_PLACEHOLDERS.get(mode, "Type your question or answer here...")
user_input = st.chat_input(placeholder)

# Handle suggestion / CTA button click
if st.session_state.pending_suggestion:
    user_input = st.session_state.pending_suggestion
    st.session_state.pending_suggestion = None

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
        with st.spinner("Thinking..."):
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
                st.error(f"Error calling OpenAI API: {e}")
