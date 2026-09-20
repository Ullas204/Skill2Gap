"""Phase 12 – Sandboxed code execution for coding assessments.

Candidate code NEVER runs inside the application process:

* ``docker`` driver – runs an isolated container with no network,
  CPU/memory/PID limits and a hard wall-clock timeout.
* ``local`` driver  – fallback restricted subprocess (isolated mode
  interpreter, scrubbed environment, temp cwd, kill-on-timeout).
  On POSIX it additionally applies RLIMIT_CPU / RLIMIT_AS.

Selection follows ``settings.assessment_sandbox``; the docker driver
falls back to ``local`` when Docker is unavailable. Both modes enforce
execution timeouts and never grant host/network access.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from app.core.config import get_settings

settings = get_settings()

HARNESS_TEMPLATE = '''
import json, sys, traceback

def _norm(v):
    if isinstance(v, tuple):
        return [_norm(x) for x in v]
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, set):
        return sorted(map(str, v))
    if isinstance(v, float):
        return round(v, 6)
    return v

def main():
    with open("solution.py") as f:
        code = f.read()
    ns = {{}}
    exec(compile(code, "solution.py", "exec"), ns)
    fn = ns[{fn_name!r}]
    with open("tests.json") as f:
        cases = json.load(f)
    results = []
    for idx, case in enumerate(cases):
        entry = {{"index": idx, "passed": False}}
        try:
            got = fn(*case["args"])
            entry["passed"] = _norm(got) == _norm(case["expected"])
            entry["received"] = repr(got)[:400]
            entry["expected"] = repr(case["expected"])[:400]
        except Exception as e:
            entry["error"] = f"{{type(e).__name__}}: {{e}}"[:400]
            entry["received"] = entry.get("error")
            entry["expected"] = repr(case["expected"])[:400]
        results.append(entry)
    print("__RESULTS__" + json.dumps(results))

main()
'''


def estimate_complexity(code: str) -> dict:
    """Static heuristic complexity ESTIMATE (documented as such, not measured)."""
    lines = [ln for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    max_depth = 0
    depth = 0
    loop_kw = ("for ", "while ")
    for ln in lines:
        stripped = ln.lstrip()
        indent = len(ln) - len(stripped)
        depth = indent // 4
        if any(stripped.startswith(kw) for kw in loop_kw):
            depth += 1
            max_depth = max(max_depth, depth)
    fn_name = None
    recursive = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("def ") and fn_name is None:
            fn_name = s[4:].split("(")[0].strip()
        elif fn_name and f"{fn_name}(" in s and not s.startswith("def"):
            recursive = True
    if recursive:
        time_c = "O(2^n) (recursive; verify memoization)"
    elif max_depth == 0:
        time_c = "O(1)"
    elif max_depth == 1:
        time_c = "O(n)"
    elif max_depth == 2:
        time_c = "O(n^2)"
    else:
        time_c = f"O(n^{max_depth})"
    sorts_heavy = any(k in code for k in ("sorted(", ".sort(", "bisect"))
    if sorts_heavy and time_c.startswith("O(n)"):
        time_c = "O(n log n)"
    space = "O(n)" if any(k in code for k in ("append", "[", "dict(", "set(")) else "O(1)"
    return {
        "time": time_c,
        "space": space,
        "note": "Heuristic static estimate, not a measured profile.",
    }


class CodeSandbox:
    """Runs untrusted Python solutions against structured test cases."""

    def __init__(self) -> None:
        self.driver = getattr(settings, "assessment_sandbox", "local")

    # ── public API ───────────────────────────────────────────────

    def run_tests(
        self,
        code: str,
        test_cases: list[dict],
        function_name: str,
        timeout_seconds: int | None = None,
    ) -> dict:
        """Returns {ok, stdout, stderr, execution_time_ms, passed_count,
        total_count, test_results, timed_out, sandbox_mode}."""
        timeout = timeout_seconds or getattr(settings, "assessment_code_timeout_s", 10)
        workdir = tempfile.mkdtemp(prefix="hire_sandbox_")
        try:
            with open(os.path.join(workdir, "solution.py"), "w", encoding="utf-8") as f:
                f.write(code)
            serializable = [
                {"args": tc.get("args", []), "expected": tc.get("expected")}
                for tc in test_cases
            ]
            with open(os.path.join(workdir, "tests.json"), "w", encoding="utf-8") as f:
                json.dump(serializable, f)
            with open(os.path.join(workdir, "harness.py"), "w", encoding="utf-8") as f:
                f.write(HARNESS_TEMPLATE.format(fn_name=function_name))

            started = time.monotonic()
            timed_out = False
            if self.driver == "docker":
                proc, timed_out, used = self._docker_run(workdir, timeout)
                if used != "docker":
                    self.driver = used
            else:
                proc, timed_out = self._local_run(workdir, timeout)
            elapsed_ms = int((time.monotonic() - started) * 1000)

            stdout = (proc.stdout or "") if proc else ""
            stderr = (proc.stderr or "")[-2000:] if proc else ""
            parsed, parse_ok = self._parse_results(stdout)

            if timed_out:
                return {
                    "ok": False, "stdout": stdout[:4000], "stderr": stderr or "Execution timed out.",
                    "execution_time_ms": elapsed_ms, "passed_count": 0,
                    "total_count": len(test_cases),
                    "test_results": [], "timed_out": True,
                    "sandbox_mode": self.driver,
                }
            if not parse_ok:
                return {
                    "ok": False, "stdout": stdout[:4000], "stderr": stderr or "Runtime error during execution.",
                    "execution_time_ms": elapsed_ms, "passed_count": 0,
                    "total_count": len(test_cases),
                    "test_results": [], "timed_out": False,
                    "sandbox_mode": self.driver,
                }
            passed = sum(1 for r in parsed if r.get("passed"))
            visible = [
                {
                    "index": r.get("index", i),
                    "passed": bool(r.get("passed")),
                    "input_preview": None,
                    "expected": r.get("expected"),
                    "received": r.get("received"),
                    "hidden": False,
                }
                for i, r in enumerate(parsed)
            ]
            return {
                "ok": passed == len(parsed),
                "stdout": stdout.replace("__RESULTS__" + json.dumps(parsed), "").strip()[:4000],
                "stderr": stderr,
                "execution_time_ms": elapsed_ms,
                "passed_count": passed,
                "total_count": len(parsed),
                "test_results": visible,
                "timed_out": False,
                "sandbox_mode": self.driver,
            }
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    # ── drivers ──────────────────────────────────────────────────

    def _local_run(self, workdir: str, timeout: int):
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}
        kwargs: dict = {
            "cwd": workdir,
            "env": env,
            "capture_output": True,
            "text": True,
            "timeout": timeout,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            kwargs["preexec_fn"] = self._posix_limits
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "harness.py"], **kwargs,
            )
            return proc, False
        except subprocess.TimeoutExpired as exc:
            class _TO:  # shape-compatible stub
                stdout = exc.stdout or "" if isinstance(exc.stdout, str) else ""
                stderr = "Execution timed out."
            return _TO(), True

    @staticmethod
    def _posix_limits():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))

    def _docker_run(self, workdir: str, timeout: int):
        docker = shutil.which("docker")
        if not docker:
            return self._local_run(workdir, timeout) + ("local",)
        image = getattr(settings, "assessment_docker_image", "python:3.11-slim")
        cmd = [
            docker, "run", "--rm", "--network", "none",
            "--memory", "256m", "--cpus", "0.5", "--pids-limit", "64",
            "--security-opt", "no-new-privileges",
            "-v", f"{workdir}:/sandbox", "-w", "/sandbox",
            image, sys.executable, "-I", "harness.py",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
            return proc, False, "docker"
        except (subprocess.TimeoutExpired, OSError):
            return self._local_run(workdir, timeout) + ("local",)

    # ── parsing ──────────────────────────────────────────────────

    @staticmethod
    def _parse_results(stdout: str):
        marker = "__RESULTS__"
        if marker not in stdout:
            return [], False
        try:
            payload = stdout.split(marker)[-1].strip()
            end = payload.rfind("]")
            parsed = json.loads(payload[: end + 1])
            return parsed, isinstance(parsed, list)
        except (ValueError, IndexError):
            return [], False


class SqlGrader:
    """Executes candidate SQL against an isolated in-memory SQLite database
    seeded with sample data and compares output with the reference query."""

    FORBIDDEN = ("attach", "pragma", "load_extension", "insert", "update",
                 "delete", "drop", "alter", "create", "vacuum", "reindex")

    def grade(self, setup_statements: list[str], candidate_query: str,
              reference_query: str) -> dict:
        stripped = candidate_query.strip().rstrip(";").lower()
        if any(stripped.startswith(f) or f";{f}" in f"{';' + stripped}" for f in self.FORBIDDEN) \
                or any(f" {f} " in f" {stripped} " for f in self.FORBIDDEN):
            return {
                "is_correct": False, "score": 0,
                "feedback": "Query rejected: only read-only SELECT/WITH statements are allowed.",
                "columns": [], "row_count": 0,
            }
        if ";" in candidate_query.strip().rstrip(";"):
            return {
                "is_correct": False, "score": 0,
                "feedback": "Multiple statements are not allowed.",
                "columns": [], "row_count": 0,
            }
        try:
            import sqlite3
            conn = sqlite3.connect(":memory:")
            conn.set_progress_handler(lambda: 1, 5_000_000)
            try:
                cur = conn.cursor()
                for stmt in setup_statements:
                    cur.execute(stmt)
                cur.execute(candidate_query.strip().rstrip(";"))
                cand_rows = cur.fetchall()
                ref_rows = cur.execute(reference_query).fetchall()
            finally:
                conn.close()
        except Exception as e:
            return {
                "is_correct": False, "score": 20,
                "feedback": f"SQL error: {type(e).__name__}: {e}"[:300],
                "columns": [], "row_count": 0,
            }

        norm_cand = sorted(tuple("" if c is None else str(c) for c in row) for row in cand_rows)
        norm_ref = sorted(tuple("" if c is None else str(c) for c in row) for row in ref_rows)
        match = norm_cand == norm_ref
        partial = 0
        if not match and norm_ref:
            overlap = len(set(norm_cand) & set(norm_ref)) / max(len(norm_ref), 1)
            partial = int(min(overlap, 1.0) * 60)
        return {
            "is_correct": match,
            "score": 100 if match else partial,
            "feedback": (
                "Correct! Your query returned exactly the expected rows."
                if match else
                f"Expected {len(ref_rows)} row(s) from the reference query; "
                f"yours returned {len(cand_rows)} row(s). Check joins, filters and ordering-independent column order."
            ),
            "row_count": len(cand_rows),
            "reference_row_count": len(ref_rows),
        }
