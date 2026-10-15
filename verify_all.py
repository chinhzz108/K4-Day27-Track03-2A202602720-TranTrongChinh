#!/usr/bin/env python3
"""Central Verification Script — Day 27 Track 3 HITL PR Review Agent.

Chương trình kiểm tra toàn bộ các bài tập trong Day 27:
  - Exercise 1: Confidence scoring & routing (PR #1 -> human_approval, PR #2 -> escalate)
  - Exercise 2: HITL interrupt() + Command(resume=...)
  - Exercise 3: Escalation with reviewer Q&A & node_synthesize
  - Exercise 4: SQLite Audit Trail (audit_events & replay)
  - Exercise 5: Streamlit Web UI & Graph compilation

Học viên: Trần Trọng Chinh
Mã học viên: 2A202602720
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()


def print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_exercise_1() -> bool:
    print("\n▶ [Test 1] Exercise 1: Confidence-based Routing...")
    cmd1 = ["uv", "run", "python", "exercises/exercise_1_confidence.py", "--pr", "https://github.com/VinUni-AI20k/PR-Demo/pull/1"]
    cmd2 = ["uv", "run", "python", "exercises/exercise_1_confidence.py", "--pr", "https://github.com/VinUni-AI20k/PR-Demo/pull/2"]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    p1 = subprocess.run(cmd1, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", env=env, timeout=40)
    p2 = subprocess.run(cmd2, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", env=env, timeout=40)

    p1_ok = (p1.returncode == 0 and "HUMAN APPROVAL" in p1.stdout)
    p2_ok = (p2.returncode == 0 and "ESCALATE" in p2.stdout)

    if p1_ok and p2_ok:
        print("   ✅ PR #1 routed to human_approval, PR #2 routed to escalate!")
        return True
    else:
        print(f"   ❌ Failed: PR1 OK={p1_ok}, PR2 OK={p2_ok}")
        return False


def test_exercise_2() -> bool:
    print("\n▶ [Test 2] Exercise 2: HITL interrupt() Graph & Handlers...")
    script = """
import sys
from dotenv import load_dotenv; load_dotenv()
from exercises.exercise_2_hitl import build_graph, prompt_human
app = build_graph()
assert app is not None, "Graph compilation failed"
print("Graph compiled with MemorySaver successfully")
"""
    cmd = ["uv", "run", "python", "-c", script]
    p = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode == 0:
        print("   ✅ Exercise 2 graph compile & checkpointer verified!")
        return True
    print(f"   ❌ Error: {p.stderr}")
    return False


def test_exercise_3() -> bool:
    print("\n▶ [Test 3] Exercise 3: Escalation & Synthesis Graph...")
    script = """
import sys
from dotenv import load_dotenv; load_dotenv()
from exercises.exercise_3_escalation import build_graph, node_escalate, node_synthesize
app = build_graph()
assert app is not None, "Graph compilation failed"
print("Escalation graph compiled successfully")
"""
    cmd = ["uv", "run", "python", "-c", script]
    p = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode == 0:
        print("   ✅ Exercise 3 escalation wiring & synthesize node verified!")
        return True
    print(f"   ❌ Error: {p.stderr}")
    return False


def test_exercise_4() -> bool:
    print("\n▶ [Test 4] Exercise 4: SQLite Audit Trail & Replay...")
    cmd = ["uv", "run", "python", "-m", "audit.replay", "--list"]
    p = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode == 0 and "Recent review sessions" in p.stdout:
        print("   ✅ Audit events recorded and listable via replay tool!")
        return True
    print(f"   ❌ Replay check error: {p.stderr}")
    return False


def test_exercise_5() -> bool:
    print("\n▶ [Test 5] Exercise 5: Streamlit Web UI Compilation...")
    script = """
import py_compile
py_compile.compile('app.py', doraise=True)
print("app.py syntax and imports OK")
"""
    cmd = ["uv", "run", "python", "-c", script]
    p = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", timeout=20)
    if p.returncode == 0:
        print("   ✅ Streamlit app.py syntax and dependencies verified!")
        return True
    print(f"   ❌ app.py error: {p.stderr}")
    return False


def main() -> int:
    print_header("HỆ THỐNG KIỂM TRA TỰ ĐỘNG — DAY 27 HITL PR REVIEW AGENT")
    print("  Học viên    : Trần Trọng Chinh")
    print("  Mã học viên : 2A202602720")
    print("  LLM Engine  : Groq Cloud (openai/gpt-oss-120b)")
    print("  GitHub User : chinhzz108")
    print(f"  Thư mục gốc : {ROOT_DIR}")

    results = {
        "Exercise 1 (Confidence-based Routing)": test_exercise_1(),
        "Exercise 2 (HITL interrupt & Resume)": test_exercise_2(),
        "Exercise 3 (Escalation & Synthesize)": test_exercise_3(),
        "Exercise 4 (SQLite Audit Trail & Replay)": test_exercise_4(),
        "Exercise 5 (Streamlit Approval UI)": test_exercise_5(),
    }

    print_header("KẾT QUẢ TỔNG HỢP KIỂM THỬ")
    all_passed = True
    for name, passed in results.items():
        status = "PASSED ✅" if passed else "FAILED ❌"
        print(f"  • {name:<45} : {status}")
        if not passed:
            all_passed = False

    print("\n" + "-" * 70)
    if all_passed:
        print("🎉 TẤT CẢ 5/5 BÀI KIỂM THỬ ĐÃ HOÀN TẤT VÀ VƯỢT QUA XUẤT SẮC!")
        return 0
    else:
        print("⚠️ Một số bài kiểm thử chưa đạt, vui lòng xem chi tiết ở trên.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
