import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path
import json


def _render_score_card(score_dict: dict) -> None:
    """Render a compact rubric score card for an answer evaluation."""
    if not score_dict:
        return
    dims = score_dict.get("dimensions", {})
    overall = score_dict.get("overall", 0)
    strength = score_dict.get("strength", "")
    improve = score_dict.get("improve", "")

    def _bar_color(v: float) -> str:
        return "#4ade80" if v >= 7 else "#fbbf24" if v >= 5 else "#f87171"

    overall_color = _bar_color(overall)
    bars_html = ""
    for dim, val in dims.items():
        pct = int(val * 10)
        warn = " ⚠" if val < 6 else ""
        bars_html += (
            f'<div class="sc-dim-row">'
            f'<span class="sc-dim-label">{dim}{warn}</span>'
            f'<div class="sc-bar-track"><div class="sc-bar-fill" '
            f'style="width:{pct}%;background:{_bar_color(val)}"></div></div>'
            f'<span class="sc-val">{val}</span>'
            f'</div>'
        )

    fb_html = ""
    if strength or improve:
        fb_html = (
            '<div class="sc-feedback">'
            + (f'<span class="sc-strength">✓ {strength}</span>' if strength else "")
            + (f'<span class="sc-improve">△ {improve}</span>' if improve else "")
            + '</div>'
        )

    st.markdown(
        f'<div class="score-card">'
        f'<div class="sc-overall">Answer Score: '
        f'<span style="color:{overall_color}">{overall}</span>'
        f'<span class="sc-denom"> / 10</span></div>'
        f'{bars_html}{fb_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


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
.role-highlight { color: #e9d5ff !important; font-weight: 600 !important; }
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

/* ── Answer Score Card ───────────────────────────────────────────────── */
.score-card {
    background: rgba(124, 58, 237, 0.07) !important;
    border: 1px solid rgba(124, 58, 237, 0.18) !important;
    border-left: 3px solid #7c3aed !important;
    border-radius: 10px !important;
    padding: 14px 16px 12px !important;
    margin: -4px 0 20px 0 !important;
    font-family: 'Inter', sans-serif !important;
}
.sc-overall {
    font-size: 0.86rem !important;
    font-weight: 600 !important;
    color: rgba(255,255,255,0.85) !important;
    margin-bottom: 10px !important;
    letter-spacing: 0.01em !important;
}
.sc-denom {
    font-weight: 400 !important;
    color: rgba(255,255,255,0.38) !important;
    font-size: 0.82rem !important;
}
.sc-dim-row {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
    margin: 5px 0 !important;
}
.sc-dim-label {
    width: 155px !important;
    font-size: 0.77rem !important;
    color: rgba(255,255,255,0.60) !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}
.sc-bar-track {
    flex: 1 !important;
    height: 3px !important;
    background: rgba(255,255,255,0.08) !important;
    border-radius: 2px !important;
    overflow: hidden !important;
}
.sc-bar-fill {
    height: 100% !important;
    border-radius: 2px !important;
}
.sc-val {
    width: 20px !important;
    text-align: right !important;
    font-size: 0.77rem !important;
    color: rgba(255,255,255,0.45) !important;
}
.sc-feedback {
    margin-top: 10px !important;
    padding-top: 8px !important;
    border-top: 1px solid rgba(255,255,255,0.06) !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
}
.sc-strength { font-size: 0.78rem !important; color: #4ade80 !important; }
.sc-improve  { font-size: 0.78rem !important; color: #fb923c !important; }
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
