import streamlit as st
from openai import OpenAI
import io
import json
from pydantic import BaseModel

from config import _INJECTION_PATTERNS, _MODE_SUGGESTION_CONTEXT, SUGGESTIONS

# Rough token budget: keep history within ~12k tokens (leaves headroom for system prompt + response)
_MAX_HISTORY_CHARS = 48_000  # ~12k tokens at ~4 chars/token


def _trim_history(messages: list[dict]) -> list[dict]:
    """Return a sliding window of messages that fits within the character budget.

    Always keeps the most recent messages. The first message (usually the
    opening assistant greeting) is dropped first when trimming is needed.
    """
    total = sum(len(m["content"]) for m in messages)
    if total <= _MAX_HISTORY_CHARS:
        return messages
    trimmed = list(messages)
    while len(trimmed) > 1 and sum(len(m["content"]) for m in trimmed) > _MAX_HISTORY_CHARS:
        trimmed.pop(0)
    return trimmed


def _is_injection(text: str) -> bool:
    """Return True if text contains a known prompt injection pattern."""
    lower = text.lower()
    return any(p in lower for p in _INJECTION_PATTERNS)


def _is_flagged_by_moderation(openai_client, text: str) -> bool:
    """Return True if OpenAI's moderation endpoint flags the text as harmful."""
    try:
        result = openai_client.moderations.create(input=text)
        return result.results[0].flagged
    except Exception:
        return False


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

def _should_score(mode: str, text: str) -> bool:
    """Return True if the user's answer is worth scoring."""
    if "Question Generator" in mode:
        return False
    return len(text.split()) >= 15


class _ScoreSchema(BaseModel):
    dimensions: dict[str, int]
    overall: float
    strength: str
    improve: str


def _score_answer(
    openai_client, question: str, answer: str, role: str, mode: str,
    resume: str = "", jd: str = "",
) -> dict | None:
    """Score a candidate's answer via gpt-4.1-nano. Returns dict or None on failure."""
    if "Behavioral" in mode:
        dimensions = ["STAR Structure", "Specificity", "Impact", "Relevance"]
    elif "Deep-Dive" in mode:
        dimensions = ["Technical Accuracy", "Problem Decomp.", "Trade-offs", "Clarity"]
    elif "Mock" in mode:
        dimensions = ["Completeness", "Clarity", "Confidence", "Relevance"]
    else:
        dimensions = ["Accuracy", "Depth", "Clarity", "Practical Application"]

    ctx = ""
    if resume.strip():
        ctx += f"\nCandidate background: {resume[:400]}"
    if jd.strip():
        ctx += f"\nTarget JD excerpt: {jd[:400]}"

    d = dimensions
    prompt = (
        f"You are an expert interview coach scoring a {role} candidate's answer.\n\n"
        f"Question/context: {question[:400]}\n"
        f"Candidate's answer: {answer[:800]}\n"
        f"{ctx}\n\n"
        f"Score each dimension 1-10 (integer): {', '.join(d)}.\n"
        f"overall is a float 1.0-10.0. strength and improve are each under 10 words."
    )
    try:
        resp = openai_client.beta.chat.completions.parse(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format=_ScoreSchema,
            temperature=0.1,
            max_tokens=220,
        )
        parsed = resp.choices[0].message.parsed
        return {
            "dimensions": parsed.dimensions,
            "overall": parsed.overall,
            "strength": parsed.strength,
            "improve": parsed.improve,
        }
    except Exception:
        return None


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
