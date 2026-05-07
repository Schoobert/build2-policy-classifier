"""Streamlit UI for the AI Policy Violation Classifier."""

import io
import sys
from pathlib import Path

# Ensure project root is on sys.path when run as `streamlit run src/ui/app.py`
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pdfplumber
import streamlit as st

from src.classifier import classify, ClassificationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_POLICY_PATH = _ROOT / "data" / "policies" / "reddit_content_policy.txt"

_VERDICT_STYLE = {
    "allowed":    ("✅", "ALLOWED",    "success"),
    "borderline": ("⚠️", "BORDERLINE", "warning"),
    "violating":  ("🚫", "VIOLATING",  "error"),
}

# Plain-language definition shown inline after the verdict banner
_VERDICT_DETAIL = {
    "allowed": (
        "Content clearly complies with the policy. **No action required.**"
    ),
    "borderline": (
        "Content is ambiguous or sits at the edge of policy language. "
        "**Recommended action:** escalate to a senior reviewer or policy team "
        "for human judgment. Do not action unilaterally."
    ),
    "violating": (
        "Content clearly breaches one or more policy provisions. "
        "**Recommended action:** action per platform enforcement guidelines."
    ),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _load_default_policy() -> str:
    try:
        return _POLICY_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using pdfplumber."""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        return "\n\n".join(
            page.extract_text() or "" for page in pdf.pages
        ).strip()


def _policy_title(policy_text: str) -> str:
    for line in policy_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return "Untitled policy"


def _confidence_tier(score: float) -> str:
    if score >= 0.80:
        return "High"
    if score >= 0.50:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# Page config  (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Policy Violation Classifier",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Session state — seed on first load
# ---------------------------------------------------------------------------

if "policy_text" not in st.session_state:
    st.session_state["policy_text"] = _load_default_policy()
if "policy_source" not in st.session_state:
    st.session_state["policy_source"] = "Reddit Content Policy"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🔍 AI Policy Violation Classifier")
st.markdown(
    "This tool is built for **Trust and Safety reviewers, content policy operators, and "
    "compliance teams** at platforms of any size. It helps content moderators make faster, "
    "more defensible decisions by classifying submitted content against any written policy — "
    "surfacing whether content is **allowed**, **borderline**, or **violating**, with direct "
    "citations to the specific policy sections that support the judgment. The Reddit Community "
    "Guidelines are loaded by default as a working example, but this tool is designed to work "
    "with any platform's policy: upload a `.txt` or `.pdf` file or paste any community "
    "guidelines directly to classify content against your own rules."
)

st.divider()

# ---------------------------------------------------------------------------
# Policy document — file upload + paste toggle
# ---------------------------------------------------------------------------

st.caption(f"**Active policy:** {st.session_state['policy_source']}")

with st.expander("📄 Policy Document (click to change)", expanded=False):

    uploaded_file = st.file_uploader(
        "Upload a policy file",
        type=["txt", "pdf"],
        help="Upload a .txt or .pdf policy document.",
        label_visibility="visible",
    )

    if uploaded_file is not None:
        if uploaded_file.type == "application/pdf":
            raw_bytes = uploaded_file.read()
            extracted = _extract_pdf_text(raw_bytes)
            if len(extracted) < 100:
                st.error(
                    "Could not extract text from this PDF. "
                    "Please upload a text file or paste the policy manually."
                )
            else:
                st.session_state["policy_text"] = extracted
                st.session_state["policy_source"] = uploaded_file.name
                st.success(f"Loaded **{uploaded_file.name}** ({len(extracted):,} characters)")
        else:
            # Plain text file
            text = uploaded_file.read().decode("utf-8", errors="replace")
            st.session_state["policy_text"] = text
            st.session_state["policy_source"] = uploaded_file.name
            st.success(f"Loaded **{uploaded_file.name}** ({len(text):,} characters)")

    paste_toggle = st.checkbox("Or paste policy manually")
    if paste_toggle:
        pasted = st.text_area(
            label="paste_policy",
            label_visibility="collapsed",
            value=st.session_state["policy_text"],
            height=360,
            placeholder="Paste the full policy text here…",
        )
        if pasted != st.session_state["policy_text"]:
            st.session_state["policy_text"] = pasted
            st.session_state["policy_source"] = "Custom (pasted)"

# Re-render the metadata line after any change this run
st.caption(f"**Active policy:** {st.session_state['policy_source']}")

# ---------------------------------------------------------------------------
# Content input
# ---------------------------------------------------------------------------

st.subheader("Content to Classify")
content_input = st.text_area(
    label="content",
    label_visibility="collapsed",
    height=180,
    placeholder="Paste the content to classify here.",
    max_chars=5000,
    key="content_input",
)

classify_btn = st.button(
    "Classify →",
    type="primary",
    use_container_width=True,
)

st.divider()

# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

if classify_btn:
    if not content_input.strip():
        st.warning("Please enter some content to classify.")
    elif not st.session_state["policy_text"].strip():
        st.warning("Please provide a policy document.")
    else:
        with st.spinner("Classifying…"):
            try:
                result = classify(
                    content_input.strip(),
                    st.session_state["policy_text"].strip(),
                )
                st.session_state["result"] = result
                st.session_state["clf_error"] = None
            except ClassificationError as exc:
                st.session_state["result"] = None
                st.session_state["clf_error"] = str(exc)

# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

if error := st.session_state.get("clf_error"):
    st.error(f"**Classification failed.** {error}")

if result := st.session_state.get("result"):
    icon, label, style = _VERDICT_STYLE[result.verdict]

    # Verdict banner
    banner = getattr(st, style)
    banner(f"### {icon} &nbsp; Verdict: **{label}**")

    # Inline verdict definition + recommended action
    st.markdown(_VERDICT_DETAIL[result.verdict])

    st.write("")

    # Metrics row
    m1, m2, m3 = st.columns(3)
    m1.metric("Verdict", label)
    m2.metric("Confidence Score", f"{result.confidence_score:.2f}")
    m3.metric("Confidence Tier", _confidence_tier(result.confidence_score))

    st.write("")

    # Reasoning
    st.subheader("💬 Reasoning")
    st.write(result.reasoning)

    # Citations
    st.subheader("📎 Policy Citations")
    if not result.cited_sections:
        st.info("No specific sections cited.")
    else:
        for i, section in enumerate(result.cited_sections, start=1):
            st.info(f"**{i}.** {section}")
