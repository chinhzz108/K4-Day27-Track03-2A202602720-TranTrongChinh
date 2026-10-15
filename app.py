"""Exercise 5 — Streamlit approval UI for the HITL PR review agent.

Run with:
    uv run streamlit run app.py

Goal: wrap the LangGraph built in exercises 1–4 in a web UI that adapts to
the confidence bucket of each PR.

Routing thresholds (common/schemas.py):
    > 72%        auto_approve     UI shows a success card; reviewer does nothing
    58 – 72%     human_approval   UI shows Approve / Reject / Edit buttons
    <  58%       escalate         UI shows a question form for the reviewer

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import uuid

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from common.db import db_path
from exercises.exercise_4_audit import build_graph

load_dotenv()


# ─── Session state ─────────────────────────────────────────────────────────
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "pr_url" not in st.session_state:
    st.session_state.pr_url = ""
if "interrupt_payload" not in st.session_state:
    st.session_state.interrupt_payload = None
if "final" not in st.session_state:
    st.session_state.final = None


# ─── Page setup ────────────────────────────────────────────────────────────
st.set_page_config(page_title="HITL PR Review Agent", layout="wide", page_icon="🤖")
st.title("🤖 HITL PR Review Agent")


# ─── Sidebar — Student Info & Recent Sessions ──────────────────────────────
def get_recent_sessions():
    try:
        conn = sqlite3.connect(db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT thread_id,
                   pr_url,
                   MIN(timestamp)        AS started,
                   MAX(timestamp)        AS last_event,
                   MAX(risk_level)       AS worst_risk,
                   COUNT(*)              AS events
              FROM audit_events
             GROUP BY thread_id, pr_url
             ORDER BY MAX(timestamp) DESC
             LIMIT 15
            """
        )
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


with st.sidebar:
    st.markdown("### 👨‍🎓 Thông tin học viên")
    st.info("**Họ và tên:** Trần Trọng Chinh\n\n**Mã học viên:** 2A202602720\n\n**GitHub:** chinhzz108")
    st.divider()

    st.header("📋 Recent Sessions")
    sessions = get_recent_sessions()
    if sessions:
        for s in sessions:
            tid = s["thread_id"]
            short_id = tid[:8]
            risk = s["worst_risk"].upper()
            label = f"🔗 {short_id} [{risk}] ({s['events']} events)"
            if st.button(label, key=f"session_{tid}", use_container_width=True):
                st.session_state.thread_id = tid
                st.session_state.pr_url = s["pr_url"]
                st.session_state.interrupt_payload = None
                st.session_state.final = None
                st.rerun()
    else:
        st.caption("No previous sessions found in audit log.")


# ─── Top form — start a new review ─────────────────────────────────────────
with st.form("start"):
    pr_url = st.text_input(
        "PR URL",
        value=st.session_state.pr_url,
        placeholder="https://github.com/VinUni-AI20k/PR-Demo/pull/1",
    )
    submitted = st.form_submit_button("🚀 Run Review", type="primary")


# ─── Renderers per interrupt kind ──────────────────────────────────────────
def render_approval_card(payload: dict) -> dict | None:
    """58–72% bucket: show the LLM review + 3 buttons. Return resume dict or None."""
    conf = payload["confidence"]
    st.subheader(f"⚠️ Approval Requested — Confidence {conf:.0%}")
    st.caption(f"**Reasoning:** {payload.get('confidence_reasoning', '')}")
    st.markdown(f"**Summary:** {payload.get('summary', '')}")

    comments = payload.get("comments", [])
    if comments:
        st.markdown("#### Proposed Comments")
        for c in comments:
            st.markdown(f"- **[{c['severity'].upper()}]** `{c['file']}:{c.get('line') or '?'}` — {c['body']}")

    with st.expander("🔍 View Diff Preview"):
        st.code(payload.get("diff_preview", ""), language="diff")

    st.divider()
    feedback = st.text_input("Reviewer Notes / Feedback (optional)", key="approval_feedback")

    col1, col2, col3 = st.columns(3)
    if col1.button("✅ Approve", type="primary", use_container_width=True):
        return {"choice": "approve", "feedback": feedback}
    if col2.button("❌ Reject", use_container_width=True):
        return {"choice": "reject", "feedback": feedback}
    if col3.button("✏️ Edit & Request Changes", use_container_width=True):
        return {"choice": "edit", "feedback": feedback}
    return None


def render_escalation_card(payload: dict) -> dict | None:
    """< 58% bucket: show risk factors + question form. Return {question: answer} or None."""
    conf = payload["confidence"]
    st.subheader(f"🚨 Strong Escalation Required — Confidence {conf:.0%}")
    st.caption(f"**Reasoning:** {payload.get('confidence_reasoning', '')}")

    risk_factors = payload.get("risk_factors")
    if risk_factors:
        st.error("**Identified Risk Factors:**\n" + "\n".join(f"- {r}" for r in risk_factors))

    st.markdown(f"**Summary:** {payload.get('summary', '')}")

    with st.form("escalation"):
        st.markdown("#### Clarification Questions from Agent")
        questions = payload.get("questions", [])
        answers: dict[str, str] = {}
        for i, q in enumerate(questions):
            answers[q] = st.text_input(f"Q{i+1}: {q}", key=f"esc_q_{i}")
        submitted_answers = st.form_submit_button("📤 Submit Answers & Re-synthesize", type="primary")
        if submitted_answers:
            return answers
    return None


# ─── Drive the graph ───────────────────────────────────────────────────────
async def run_graph(pr_url: str, thread_id: str, resume_value=None):
    """Invoke the graph once. Returns the final result or {'__interrupt__': ...}."""
    async with AsyncSqliteSaver.from_conn_string(db_path()) as cp:
        await cp.setup()
        app = build_graph(cp)
        cfg = {"configurable": {"thread_id": thread_id}}

        if resume_value is None:
            result = await app.ainvoke({"pr_url": pr_url, "thread_id": thread_id}, cfg)
        else:
            result = await app.ainvoke(Command(resume=resume_value), cfg)
        return result


# ─── Main flow ─────────────────────────────────────────────────────────────
if submitted and pr_url:
    st.session_state.pr_url = pr_url
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.interrupt_payload = None
    st.session_state.final = None

    with st.spinner("Fetching PR & analyzing diff with LLM..."):
        result = asyncio.run(run_graph(pr_url, st.session_state.thread_id))

    if "__interrupt__" in result:
        st.session_state.interrupt_payload = result["__interrupt__"][0].value
    else:
        st.session_state.final = result

# Render the current interrupt card, if any
payload = st.session_state.interrupt_payload
if payload is not None:
    kind = payload["kind"]
    answer = render_approval_card(payload) if kind == "approval_request" else render_escalation_card(payload)
    if answer is not None:
        with st.spinner("Resuming agent execution..."):
            result = asyncio.run(run_graph(
                st.session_state.pr_url,
                st.session_state.thread_id,
                resume_value=answer,
            ))
        if "__interrupt__" in result:
            st.session_state.interrupt_payload = result["__interrupt__"][0].value
        else:
            st.session_state.interrupt_payload = None
            st.session_state.final = result
        st.rerun()

# Render final state, if reached
if st.session_state.final is not None:
    final = st.session_state.final
    action = final.get("final_action", "?")
    analysis = final.get("analysis")

    st.divider()
    if action.startswith("auto") or action.startswith("committed"):
        conf_str = f" (Confidence {analysis.confidence:.0%})" if analysis else ""
        st.success(f"🎉 **Review Successfully Posted!** Action: `{action}`{conf_str}")
        if analysis:
            st.markdown(f"**Final Summary:** {analysis.summary}")
        st.markdown(f"👉 [**View comment directly on GitHub**]({st.session_state.pr_url})")
    elif action == "rejected":
        st.warning("⚠️ **Review Rejected** — no comment posted to the PR.")
    else:
        st.info(f"Final Action: `{action}`")

    st.caption(
        f"**Session Thread ID:** `{st.session_state.thread_id}`  ·  "
        f"**Replay CLI:** `uv run python -m audit.replay --thread {st.session_state.thread_id}`"
    )
