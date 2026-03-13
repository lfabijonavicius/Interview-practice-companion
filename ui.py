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
    CSS is loaded from static/theme.css at runtime.
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

    _CSS = (Path(__file__).parent / "static" / "theme.css").read_text()
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
