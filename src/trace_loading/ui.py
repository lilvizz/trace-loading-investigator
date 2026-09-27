from pathlib import Path
import sys
import html

SRC_DIR = Path(__file__).resolve().parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import streamlit as st

from trace_loading.data_loader import ManufacturingData
from trace_loading.agent import InvestigationAgent


# =========================================================
# Configuration
# =========================================================

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

st.set_page_config(
    page_title="TRACE — Loading Investigation",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Styling
# =========================================================

st.markdown(
    """
    <style>

    /* ---------- Global ---------- */

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    .main-title {
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-bottom: 0;
    }

    .subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-top: 0.2rem;
        margin-bottom: 1.8rem;
    }

    .section-label {
        color: #6b7280;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    /* ---------- Result ---------- */

    .result-card {
        padding: 1.35rem 1.5rem;
        border-radius: 14px;
        border: 1px solid #d1d5db;
        background: #f9fafb;
        margin: 0.4rem 0 1rem 0;
    }

    .result-card.no-exception {
        border-left: 6px solid #16a34a;
    }

    .result-card.unresolved {
        border-left: 6px solid #f59e0b;
    }

    .result-card.insufficient {
        border-left: 6px solid #eab308;
    }

    .result-card.legitimate {
        border-left: 6px solid #2563eb;
    }

    .result-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }

    .result-description {
        color: #4b5563;
        margin-top: 0.4rem;
        line-height: 1.5;
    }

    /* ---------- Metrics ---------- */

    .metric-card {
        padding: 0.9rem 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        background: #ffffff;
        min-height: 76px;
    }

    .metric-label {
        color: #6b7280;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .metric-value {
        font-size: 1.1rem;
        font-weight: 750;
        margin-top: 0.25rem;
    }

    /* ---------- Requirement ---------- */

    .requirement-card {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        background: #ffffff;
    }

    .requirement-value {
        font-size: 1.15rem;
        font-weight: 750;
        margin-top: 0.2rem;
    }

    /* ---------- Findings ---------- */

    .finding-card {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.65rem;
        background: #ffffff;
    }

    .finding-type {
        font-weight: 750;
        font-size: 0.9rem;
    }

    .finding-message {
        color: #4b5563;
        margin-top: 0.3rem;
        line-height: 1.45;
    }

    /* ---------- Evidence gaps ---------- */

    .gap-card {
        border-left: 4px solid #f59e0b;
        border-top: 1px solid #f3f4f6;
        border-right: 1px solid #f3f4f6;
        border-bottom: 1px solid #f3f4f6;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.6rem;
        background: #fffbeb;
    }

    .gap-type {
        font-weight: 750;
        font-size: 0.85rem;
    }

    .gap-description {
        color: #4b5563;
        margin-top: 0.25rem;
    }

    /* ---------- Evidence ---------- */

    .evidence-card {
        border: 1px solid #e5e7eb;
        border-radius: 9px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.55rem;
        background: #ffffff;
    }

    .evidence-id {
        font-weight: 750;
    }

    .evidence-meta {
        color: #6b7280;
        font-size: 0.84rem;
        margin-top: 0.25rem;
        line-height: 1.45;
    }

    /* ---------- Investigation plan ---------- */

    .question-card {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: center;
        border-bottom: 1px solid #f0f0f0;
        padding: 0.8rem 0;
    }

    .question-text {
        font-weight: 600;
    }

    .question-reason {
        color: #6b7280;
        font-size: 0.82rem;
        margin-top: 0.2rem;
    }

    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.55rem;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 750;
        white-space: nowrap;
    }

    .status-answered {
        background: #dcfce7;
        color: #166534;
    }

    .status-unresolved {
        background: #fef3c7;
        color: #92400e;
    }

    .status-na {
        background: #f3f4f6;
        color: #4b5563;
    }

    /* ---------- Action ---------- */

    .action-card {
        border: 1px solid #dbeafe;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        background: #eff6ff;
        line-height: 1.5;
    }

    /* ---------- Safety footer ---------- */

    .safety-note {
        padding: 0.8rem 1rem;
        border: 1px solid #e5e7eb;
        border-radius: 9px;
        background: #f9fafb;
        color: #6b7280;
        font-size: 0.82rem;
        line-height: 1.45;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Data / Agent
# =========================================================

@st.cache_resource
def load_agent():
    data = ManufacturingData(DATA_DIR)
    return InvestigationAgent(data, use_gemini=False)


@st.cache_data
def get_container_ids():
    data = ManufacturingData(DATA_DIR)
    return data.loading["container_id"].dropna().tolist()


agent = load_agent()
container_ids = get_container_ids()


# =========================================================
# Helpers
# =========================================================

def safe_value(value, default="—"):
    if value is None:
        return default

    try:
        if hasattr(value, "item"):
            value = value.item()
    except Exception:
        pass

    if str(value).strip() == "":
        return default

    return value


def clean_text(value):
    return html.escape(str(safe_value(value)))


def conclusion_meta(conclusion):
    return {
        "NO_EXCEPTION": {
            "icon": "🟢",
            "class": "no-exception",
            "label": "NO EXCEPTION",
            "description": (
                "The available evidence supports the loading requirement "
                "and no unresolved exception was identified."
            ),
        },
        "UNRESOLVED": {
            "icon": "🟠",
            "class": "unresolved",
            "label": "UNRESOLVED",
            "description": (
                "TRACE identified an operational inconsistency or requirement "
                "gap that cannot be resolved from the available evidence."
            ),
        },
        "INSUFFICIENT_EVIDENCE": {
            "icon": "🟡",
            "class": "insufficient",
            "label": "INSUFFICIENT EVIDENCE",
            "description": (
                "The available records are not sufficient to establish "
                "whether the loading requirement is satisfied."
            ),
        },
        "LEGITIMATE_EXCEPTION": {
            "icon": "🔵",
            "class": "legitimate",
            "label": "LEGITIMATE EXCEPTION",
            "description": (
                "A requirement difference is supported by a documented "
                "approved substitution, waiver, or deviation."
            ),
        },
    }.get(
        conclusion,
        {
            "icon": "⚪",
            "class": "",
            "label": str(conclusion),
            "description": "TRACE returned an unclassified investigation result.",
        },
    )


def render_metric(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{clean_text(label)}</div>
            <div class="metric-value">{clean_text(value)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_quantity(value):
    value = safe_value(value)

    if value == "—":
        return value

    try:
        number = float(value)
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}"
    except Exception:
        return str(value)


def render_requirement_card(label, value, subtext=None):
    subtext_html = (
        f'<div class="metric-label">{clean_text(subtext)}</div>'
        if subtext
        else ""
    )

    st.markdown(
        f"""
        <div class="requirement-card">
            <div class="metric-label">{clean_text(label)}</div>
            <div class="requirement-value">{clean_text(value)}</div>
            {subtext_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_findings(findings):
    if not findings:
        st.success("No findings were recorded.")
        return

    for finding in findings:
        if not isinstance(finding, dict):
            st.markdown(
                f'<div class="finding-card">{clean_text(finding)}</div>',
                unsafe_allow_html=True,
            )
            continue

        finding_type = (
            finding.get("type")
            or finding.get("finding_type")
            or finding.get("status")
            or "Finding"
        )

        message = (
            finding.get("message")
            or finding.get("description")
            or finding.get("reason")
            or "No additional description was provided."
        )

        details = []

        if finding.get("required_quantity") is not None:
            details.append(
                f"Required: {format_quantity(finding['required_quantity'])}"
            )

        if finding.get("qualifying_quantity") is not None:
            details.append(
                f"Qualifying: {format_quantity(finding['qualifying_quantity'])}"
            )

        if finding.get("required_grade") is not None:
            details.append(
                f"Required grade: {finding['required_grade']}"
            )

        if details:
            detail_html = (
                '<div class="evidence-meta">'
                + " · ".join(clean_text(item) for item in details)
                + "</div>"
            )
        else:
            detail_html = ""

        st.markdown(
            f"""
            <div class="finding-card">
                <div class="finding-type">⚠️ {clean_text(finding_type)}</div>
                <div class="finding-message">{clean_text(message)}</div>
                {detail_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence_gaps(gaps):
    if not gaps:
        st.success("No unresolved evidence gaps identified.")
        return

    for gap in gaps:
        if isinstance(gap, dict):
            gap_type = gap.get("type", "Evidence gap")
            description = (
                gap.get("description")
                or gap.get("message")
                or gap.get("reason")
                or "Additional evidence is required."
            )
        else:
            gap_type = "Evidence gap"
            description = str(gap)

        st.markdown(
            f"""
            <div class="gap-card">
                <div class="gap-type">⚠️ {clean_text(gap_type)}</div>
                <div class="gap-description">{clean_text(description)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_investigation_plan(plan):
    questions = plan.get("questions", []) or []

    if not questions:
        st.info("No investigation questions available.")
        return

    complete = bool(plan.get("investigation_complete"))

    if complete:
        st.success("Investigation complete — all required questions are resolved.")
    else:
        st.warning(
            "Investigation requires human verification before the discrepancy "
            "can be cleared."
        )

    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            question_text = str(question)
            status = "ANSWERED"
            reason = ""
        else:
            question_text = (
                question.get("question")
                or question.get("text")
                or question.get("description")
                or str(question)
            )

            status = str(question.get("status", "ANSWERED")).upper()
            reason = question.get("reason", "")

        if status == "NOT_APPLICABLE":
            status_class = "status-na"
            icon = "—"
        elif status in {"UNRESOLVED", "OPEN", "PENDING"}:
            status_class = "status-unresolved"
            icon = "!"
        else:
            status_class = "status-answered"
            icon = "✓"

        st.markdown(
            f"""
            <div class="question-card">
                <div>
                    <div class="question-text">
                        Q{index}. {clean_text(question_text)}
                    </div>
                    <div class="question-reason">
                        {clean_text(reason) if reason else ""}
                    </div>
                </div>
                <span class="status-pill {status_class}">
                    {icon} {clean_text(status)}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_evidence_item(item):
    if not isinstance(item, dict):
        st.markdown(
            f'<div class="evidence-card">{clean_text(item)}</div>',
            unsafe_allow_html=True,
        )
        return

    evidence_type = item.get("type", "Evidence")

    identifier = (
        item.get("event_id")
        or item.get("bundle_id")
        or item.get("batch_id")
        or item.get("material_id")
        or item.get("reference_id")
        or evidence_type
    )

    fields = []

    preferred_fields = [
        ("material_id", "Material"),
        ("batch_id", "Batch"),
        ("quantity", "Quantity"),
        ("composition_grade", "Grade"),
        ("required_composition_grade", "Required grade"),
        ("sent_to_logistics", "Sent to logistics"),
        ("status", "Status"),
        ("event_type", "Event type"),
        ("description", "Description"),
    ]

    for key, label in preferred_fields:
        value = item.get(key)

        if value is None or value == "":
            continue

        if key == "quantity":
            value = format_quantity(value)

        fields.append(f"{label}: {value}")

    meta = " · ".join(clean_text(field) for field in fields)

    st.markdown(
        f"""
        <div class="evidence-card">
            <div class="evidence-id">
                {clean_text(evidence_type)} · {clean_text(identifier)}
            </div>
            <div class="evidence-meta">
                {meta if meta else "No additional evidence metadata."}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Header
# =========================================================

st.markdown(
    '<div class="main-title">🔎 TRACE</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    "Loading Investigation & Evidence Assistant"
    "</div>",
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar
# =========================================================

with st.sidebar:
    st.markdown("### Investigation")

    default_container = "CNT-5203"

    if default_container in container_ids:
        default_index = container_ids.index(default_container)
    else:
        default_index = 0

    selected_container = st.selectbox(
        "Loading container",
        container_ids,
        index=default_index,
    )

    st.divider()

    st.caption("Recommended demo cases")

    st.markdown(
        """
        **CNT-5203**  
        Grade mismatch + quantity issue → unresolved

        **CNT-5208**  
        Grade mismatch → approved exception

        **CNT-5207**  
        Clean loading → no exception

        **CNT-5204 / CNT-5206**  
        Missing bundle evidence
        """
    )

    st.divider()

    st.caption(
        "TRACE investigates operational evidence. "
        "It does not automatically authorize loading or modify operational records."
    )


# =========================================================
# Run investigation
# =========================================================

try:
    result = agent.investigate(selected_container)
except Exception as exc:
    st.error(f"Investigation failed: {exc}")
    st.stop()


container = result.get("container", {})
assessment = result.get("assessment", {})
requirement = result.get("requirement", {})
plan = result.get("investigation_plan", {})
findings = result.get("findings", [])
evidence = result.get("evidence", [])
evidence_gaps = result.get("evidence_gaps", [])
reason = result.get("reason", "")
recommended_action = result.get("recommended_action", "")
supporting_evidence = result.get("supporting_evidence", [])

conclusion = assessment.get("conclusion", "UNKNOWN")
confidence = assessment.get("confidence")
priority = assessment.get("priority")
requires_human = assessment.get("requires_human_verification")

meta = conclusion_meta(conclusion)


# =========================================================
# Loading case
# =========================================================

st.markdown(
    '<div class="section-label">Loading operation</div>',
    unsafe_allow_html=True,
)

st.subheader(
    f"{safe_value(container.get('id'))} · "
    f"{safe_value(container.get('destination'))}"
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    render_metric("Loading date", container.get("loading_date"))

with c2:
    render_metric("Destination", container.get("destination"))

with c3:
    render_metric("Operational status", container.get("status"))

with c4:
    render_metric("Priority", priority)


# =========================================================
# Requirement
# =========================================================

st.markdown(
    '<div class="section-label">Loading requirement</div>',
    unsafe_allow_html=True,
)

r1, r2, r3 = st.columns(3)

with r1:
    render_requirement_card(
        "Material",
        requirement.get("material_id"),
    )

with r2:
    render_requirement_card(
        "Required quantity",
        f"{format_quantity(requirement.get('required_quantity'))} EA",
    )

with r3:
    grade = requirement.get("required_composition_grade")

    render_requirement_card(
        "Required composition grade",
        grade if grade else "Not specified",
        "Grade validation is not applicable for this loading operation."
        if not grade
        else None,
    )


# =========================================================
# Investigation result
# =========================================================

st.markdown(
    '<div class="section-label">Investigation assessment</div>',
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="result-card {meta['class']}">
        <div class="result-title">
            {meta['icon']} {clean_text(meta['label'])}
        </div>
        <div class="result-description">
            {clean_text(meta['description'])}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

m1, m2, m3 = st.columns(3)

with m1:
    render_metric("Confidence", f"{float(confidence):.0%}" if confidence is not None else "—")

with m2:
    render_metric("Human verification", "Required" if requires_human else "Not required")

with m3:
    render_metric("Evidence gaps", len(evidence_gaps))


# =========================================================
# Why TRACE reached this result
# =========================================================

st.markdown(
    '<div class="section-label">Investigation reasoning</div>',
    unsafe_allow_html=True,
)

st.subheader("Why TRACE reached this result")

if reason:
    st.info(reason)
else:
    st.info("No reasoning summary was returned.")


# =========================================================
# Findings + gaps
# =========================================================

left, right = st.columns(2)

with left:
    st.subheader("Findings")
    render_findings(findings)

with right:
    st.subheader("Evidence gaps")
    render_evidence_gaps(evidence_gaps)


# =========================================================
# Investigation plan
# =========================================================

st.subheader("Investigation plan")

with st.expander(
    "Show investigation trail",
    expanded=True,
):
    render_investigation_plan(plan)


# =========================================================
# Evidence trail
# =========================================================

st.subheader("Evidence trail")

st.caption(
    "Requirement → Material → Batch → Composition Grade → "
    "Physical Bundle → Operational Event"
)

if evidence:
    for item in evidence:
        render_evidence_item(item)
else:
    st.info("No evidence records were returned.")


# =========================================================
# Supporting evidence
# =========================================================

if supporting_evidence:
    with st.expander("Supporting evidence"):
        for item in supporting_evidence:
            st.markdown(f"• `{clean_text(item)}`")


# =========================================================
# Recommended action
# =========================================================

st.subheader("Recommended human action")

if recommended_action:
    st.markdown(
        f"""
        <div class="action-card">
            <strong>Next step</strong><br>
            {clean_text(recommended_action)}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No recommended action was returned.")


# =========================================================
# Footer
# =========================================================

st.divider()

st.markdown(
    """
    <div class="safety-note">
        <strong>TRACE operating boundary:</strong>
        TRACE investigates loading evidence and surfaces discrepancies,
        evidence gaps, and recommended verification steps.
        It does <strong>not</strong> automatically authorize loading,
        modify ERP records, or replace human operational approval.
    </div>
    """,
    unsafe_allow_html=True,
)