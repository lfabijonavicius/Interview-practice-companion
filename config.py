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

_MODE_SUGGESTION_CONTEXT = {
    "General Q&A (Zero-Shot)":             "concise interview questions about concepts and technical skills",
    "Behavioral Interview (Few-Shot)":     "behavioral/situational questions using the STAR method",
    "Deep-Dive Questions (Chain-of-Thought)": "complex problems requiring step-by-step analysis",
    "Mock Interviewer (Role-Play)":        "opening lines to kick off a mock interview session",
    "Question Generator (Structured Output)": "topics or skill areas to generate a question bank from",
}
