import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from dotenv import load_dotenv
import os
from streamlit_mic_recorder import mic_recorder

from prompts import PROMPTS
from config import (
    MAX_INPUT_LENGTH, MAX_ROLE_LENGTH, MODEL_OPTIONS, MODEL_LABELS,
    MODEL_COSTS, STYLE_PRESETS, _MODEL_ICON_MAP, _MODEL_SUBTITLE_MAP,
    _PERSONA_SUBTITLE_MAP, MODE_ICONS, MODE_SHORT, MODE_SUBTITLES,
    MODE_PLACEHOLDERS, CTA_LABELS, SUGGESTIONS, MAX_JD_LENGTH,
    PERSONA_MODIFIERS,
)
from services import (
    _is_injection, _is_flagged_by_moderation, _transcribe_audio,
    _should_score, _score_answer, _fetch_suggestions,
    _temp_label, _top_p_label, _tokens_label, _freq_label, _presence_label,
    _trim_history,
)
from ui import fluid_dropdown, inject_futuristic_theme, _render_score_card
from session import initialize_session, reset_chat

load_dotenv()

st.set_page_config(page_title="Interview Practice", page_icon="💼", layout="wide")

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

with st.sidebar.expander("Your Profile (optional)", expanded=False):
    st.caption("Resume · add your background for personalised scoring")
    st.text_area(
        "Resume highlights",
        key="resume",
        height=90,
        max_chars=1500,
        placeholder="Key skills, years of experience, past roles…",
        label_visibility="collapsed",
    )
    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    st.caption("Job Description · paste the posting for tailored questions")
    st.text_area(
        "Paste the job posting",
        key="jd_input",
        height=110,
        max_chars=MAX_JD_LENGTH,
        placeholder="e.g. Senior Software Engineer at Acme Corp...\n\nResponsibilities:\n- Build scalable APIs\n- Lead code reviews...",
        help="Paste the actual job description to get tailored questions and advice for that specific role.",
        label_visibility="collapsed",
    )

resume_text = st.session_state.get("resume", "")
job_description = st.session_state.get("jd_input", "")

if resume_text and _is_injection(resume_text):
    st.sidebar.error("⚠️ Resume contains disallowed content.")
    resume_text = ""
if job_description and _is_injection(job_description):
    st.sidebar.error("⚠️ Job description contains disallowed content.")
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
    st.session_state.scores = {}
    st.rerun()

# --- API Key Validation ---
api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
if not api_key or api_key == "your-key-here":
    st.error(
        "OpenAI API key not found. Please create a `.env` file with your key:\n\n"
        "```\nOPENAI_API_KEY=sk-...\n```"
    )
    st.stop()

client = OpenAI(api_key=api_key, max_retries=3)

# --- Chat History & Session State ---
initialize_session(mode, model, job_role, persona)
reset_chat(mode, job_role, model, persona)

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
    st.markdown(f"""
<div class="welcome-card-premium">
  <div class="welcome-header">
    <svg class="welcome-icon" xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>
      <path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>
    </svg>
    <h2 class="welcome-title">{_mode_short}</h2>
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
for _i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
    # Score card appears after the assistant message that follows a scored user answer
    if msg["role"] == "assistant" and (_i - 1) in st.session_state.scores:
        _render_score_card(st.session_state.scores[_i - 1])

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

# ── Performance Tracker ───────────────────────────────────────────────
if st.session_state.scores:
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Performance Tracker")
    # Aggregate scores across all scored answers
    _all_dims: dict[str, list[float]] = {}
    for _s in st.session_state.scores.values():
        for _dim, _val in _s.get("dimensions", {}).items():
            _all_dims.setdefault(_dim, []).append(float(_val))

    for _dim, _vals in _all_dims.items():
        _avg = sum(_vals) / len(_vals)
        _icon = "🟢" if _avg >= 7 else "🟡" if _avg >= 5 else "🔴"
        st.sidebar.caption(f"{_icon} **{_dim}**: {_avg:.1f} / 10")

    # Weak spot callout
    _weakest_dim, _weakest_vals = min(_all_dims.items(), key=lambda x: sum(x[1]) / len(x[1]))
    _weakest_avg = sum(_weakest_vals) / len(_weakest_vals)
    if _weakest_avg < 7.5:
        st.sidebar.warning(f"Focus area: **{_weakest_dim}** ({_weakest_avg:.1f}/10)")

# --- Voice Input ---
with st.sidebar:
    audio_data = mic_recorder(
        start_prompt="START",
        stop_prompt="STOP",
        just_once=True,
        key="permanent_mic",
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

    # Security: prompt injection detection (pattern matching)
    if _is_injection(user_input):
        st.error(
            "⚠️ Your message contains disallowed content. "
            "Please keep your questions interview-related."
        )
        st.stop()

    # Security: OpenAI moderation endpoint (catches harmful content patterns miss)
    if _is_flagged_by_moderation(client, user_input):
        st.error(
            "⚠️ Your message was flagged by our content filter. "
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
    # Inject resume context if provided
    if resume_text.strip():
        system_prompt += (
            f"\n\nCANDIDATE BACKGROUND:\n"
            f"The candidate has the following experience. Calibrate question difficulty, "
            f"examples, and feedback to their level:\n\n{resume_text[:1000]}"
        )
    api_messages = [{"role": "system", "content": system_prompt}]
    for msg in _trim_history(st.session_state.messages):
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
            stream = client.chat.completions.create(
                model=model,
                messages=api_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=True,
                stream_options={"include_usage": True},
            )
            thinking_placeholder.empty()

            chunks = []
            def _token_gen():
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        token = chunk.choices[0].delta.content
                        chunks.append(token)
                        yield token
                    if chunk.usage:
                        st.session_state.total_input_tokens += chunk.usage.prompt_tokens
                        st.session_state.total_output_tokens += chunk.usage.completion_tokens

            st.write_stream(_token_gen())
            assistant_message = "".join(chunks)
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_message}
            )

            # Score the user's answer if it's substantive enough
            if _should_score(mode, user_input):
                with st.spinner("Scoring your answer…"):
                    # Use the last assistant message (the question) as context
                    _question_ctx = ""
                    msgs = st.session_state.messages
                    if len(msgs) >= 3 and msgs[-3]["role"] == "assistant":
                        _question_ctx = msgs[-3]["content"][:500]
                    _score = _score_answer(
                        client, _question_ctx, user_input, job_role, mode,
                        resume=resume_text, jd=job_description,
                    )
                if _score:
                    _user_idx = len(st.session_state.messages) - 2
                    st.session_state.scores[_user_idx] = _score
                    _render_score_card(_score)
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

# --- Mic SVG icon injector + chat input floater (Stable Anchor) ---
components.html("""
<script>
(function () {
  const anchorMic = () => {
    const parentDoc = window.parent.document;
    const chatInput = parentDoc.querySelector('[data-testid="stChatInput"]');
    const iframes = parentDoc.querySelectorAll('iframe[title*="streamlit_mic_recorder"]');

    iframes.forEach(iframe => {
      // 1. Keep the indestructible positioning
      const container = iframe.closest('div[data-testid="stElementContainer"]');
      if (container && chatInput) {
        container.style.cssText = [
          'display: block',
          'visibility: visible',
          'opacity: 1',
          'position: fixed',
          'z-index: 999999',
          'width: 44px',
          'height: 44px',
        ].join(' !important; ') + ' !important;';

        const rect = chatInput.getBoundingClientRect();
        container.style.left = (rect.left + 14) + 'px';
        container.style.top  = (rect.top + (rect.height - 44) / 2) + 'px';

        const textarea = chatInput.querySelector('textarea');
        if (textarea) textarea.style.paddingLeft = '50px';
      }

      // 2. Stable CSS injection + lightweight class toggling
      try {
        const innerDoc = iframe.contentDocument || iframe.contentWindow.document;
        if (innerDoc) {
          // Inject CSS only once per iframe render
          if (!innerDoc.getElementById('mic-stable-css')) {
            const style = innerDoc.createElement('style');
            style.id = 'mic-stable-css';
            style.innerHTML = `
              body { margin: 0 !important; background: transparent !important; }
              button {
                width: 40px !important;
                height: 40px !important;
                border-radius: 50% !important;
                background-color: transparent !important;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%23a855f7' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z'%3E%3C/path%3E%3Cpath d='M19 10v2a7 7 0 0 1-14 0v-2'%3E%3C/path%3E%3Cline x1='12' x2='12' y1='19' y2='22'%3E%3C/line%3E%3C/svg%3E") !important;
                background-position: center !important;
                background-repeat: no-repeat !important;
                background-size: 20px 20px !important;
                border: none !important;
                color: transparent !important;
                font-size: 0 !important;
                box-shadow: none !important;
                cursor: pointer !important;
                outline: none !important;
                transition: all 0.2s ease !important;
              }
              button:hover {
                background-color: rgba(255, 255, 255, 0.05) !important;
                transform: scale(1.05) !important;
              }
              button.is-recording {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='20' height='20' viewBox='0 0 24 24' fill='none' stroke='%23ef4444' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='6' y='6' width='12' height='12' rx='2' ry='2'%3E%3C/rect%3E%3C/svg%3E") !important;
                background-color: rgba(239, 68, 68, 0.1) !important;
              }
            `;
            innerDoc.head.appendChild(style);
          }

          // Lightweight class toggle based on text state
          const btn = innerDoc.querySelector('button');
          if (btn) {
            const btnText = btn.innerText || '';
            if (btnText.includes('STOP')) {
              btn.classList.add('is-recording');
            } else {
              btn.classList.remove('is-recording');
            }
          }
        }
      } catch(e) {}
    });
  };

  setInterval(anchorMic, 50);
})();
</script>
""", height=0)
