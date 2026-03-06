import streamlit as st


def initialize_session(mode: str, model: str, job_role: str, persona: str) -> None:
    """Initialize all session state variables on first run."""
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
    if "scores" not in st.session_state:
        st.session_state.scores = {}  # {user_msg_index: score_dict}
    if "resume" not in st.session_state:
        st.session_state.resume = ""
    if "jd_input" not in st.session_state:
        st.session_state.jd_input = ""
    if "current_persona" not in st.session_state:
        st.session_state.current_persona = persona
    if "interviewer_avatar_url" not in st.session_state:
        st.session_state.interviewer_avatar_url = None
    if "interviewer_avatar_role" not in st.session_state:
        st.session_state.interviewer_avatar_role = None


def reset_chat(mode: str, job_role: str, model: str, persona: str) -> None:
    """Reset chat when mode, role, model, or persona changes."""
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
        st.session_state.scores = {}
        st.session_state.current_mode = mode
        st.session_state.current_role = job_role
        st.session_state.current_model = model
        st.session_state.current_persona = persona
