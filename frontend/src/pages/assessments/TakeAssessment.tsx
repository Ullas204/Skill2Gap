import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { assessmentApi } from "../../api/assessment";
import type {
  AnswerResultResponse,
  AttemptStartResponse,
  AttemptState,
  CodeRunResponse,
  QuestionPublic,
} from "../../types/assessment";

const OBJECTIVE = new Set([
  "mcq", "aptitude_quantitative", "aptitude_logical", "aptitude_verbal",
  "technical_theory", "sql_mcq", "code_output",
]);
const SUBJECTIVE = new Set([
  "debugging", "system_design", "scenario", "case_study",
  "behavioral", "situational_judgment",
]);

function fmtTime(seconds: number): string {
  const m = Math.floor(Math.max(seconds, 0) / 60);
  const s = Math.max(seconds, 0) % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function TakeAssessment() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const [searchParams] = useSearchParams();
  const resumeAttemptId = searchParams.get("resume");
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<AttemptStartResponse | null>(null);
  const [state, setState] = useState<AttemptState | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [idx, setIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [text, setText] = useState("");
  const [code, setCode] = useState("");
  const [runResult, setRunResult] = useState<CodeRunResponse | null>(null);
  const [lastResult, setLastResult] = useState<AnswerResultResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const submittedRef = useRef(false);

  const attemptId = activeId;

  const finalize = useCallback(async () => {
    if (!attemptId || submittedRef.current) return;
    submittedRef.current = true;
    try {
      await assessmentApi.submitAttempt(attemptId);
    } finally {
      navigate(`/candidate/assessments/results/${attemptId}`);
    }
  }, [attemptId, navigate]);

  // Start the attempt (or resume an existing one) and load state.
  async function beginAttempt(id: string) {
    try {
      const started = await assessmentApi.start(id);
      setAttempt(started);
      setActiveId(started.attempt_id);
    } catch (err) {
      handleBeginError(err, id);
    }
  }

  function handleBeginError(err: unknown, id: string) {
    const status = (err as { response?: { status?: number } })?.response?.status;

    if (status === 409) {
      // Attempts exhausted: resume the live attempt or point at its result.
      void (async () => {
        try {
          const mine = await assessmentApi.myAttempts();
          const live = mine.items.find(
            (a) => a.assessment_id === id && a.status === "in_progress",
          );
          if (live) {
            navigate(`/candidate/assessments/take/${id}?resume=${live.attempt_id}`, { replace: true });
            return;
          }
          const done = mine.items.find((a) => a.assessment_id === id && a.submitted_at);
          setError(done
            ? "You have already completed this assessment. Open its result from My Assessments."
            : "No attempts remain for this assessment.");
        } catch {
          setError("No attempts remain for this assessment.");
        }
      })();
      return;
    }
    if (status === 403) {
      setError("Only candidate accounts can take assessments. Please sign in with a candidate account.");
      return;
    }
    if (status === 404) {
      setError("This assessment link is invalid or no longer exists.");
      return;
    }
    setError("Could not start this assessment. Please try again.");
  }

  useEffect(() => {
    if (!assessmentId) return;
    if (resumeAttemptId) {
      setActiveId(resumeAttemptId);
      return;
    }
    let cancelled = false;
    (async () => {
      if (!cancelled) await beginAttempt(assessmentId);
    })();
    return () => {
      cancelled = true;
    };
  }, [assessmentId, resumeAttemptId]);

  // Load (and later refresh) the sanitized attempt state.
  useEffect(() => {
    if (!attemptId) return;
    let cancelled = false;
    (async () => {
      try {
        const st = await assessmentApi.state(attemptId);
        if (cancelled) return;
        setState(st);
        if (st.status !== "in_progress") {
          navigate(`/candidate/assessments/results/${st.attempt_id}`, { replace: true });
        }
      } catch {
        if (!cancelled) setError("Could not load this assessment attempt.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [attemptId, navigate]);

  // Integrity event logging.
  useEffect(() => {
    if (!attemptId) return;
    const report = (event_type: string, detail?: string) => {
      assessmentApi.integrityEvent(attemptId, event_type, detail).catch(() => undefined);
    };
    const onVisibility = () => document.hidden && report("tab_switch");
    const onBlur = () => report("window_blur");
    const onCopy = () => report("copy_paste", "copy event");
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    document.addEventListener("copy", onCopy);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("copy", onCopy);
    };
  }, [attemptId]);

  // Countdown timer; auto-submit at zero.
  useEffect(() => {
    if (!state?.expires_at) return;
    const target = new Date(state.expires_at + (state.expires_at.endsWith("Z") ? "" : "Z")).getTime();
    const tick = () => {
      const left = Math.floor((target - Date.now()) / 1000);
      setSecondsLeft(left);
      if (left <= 0) void finalize();
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [state?.expires_at, finalize]);

  const question: QuestionPublic | null =
    state && state.questions.length > 0 ? state.questions[Math.min(idx, state.questions.length - 1)] : null;

  function isAnswered(qid: string): boolean {
    return Boolean(state?.answered?.[qid]);
  }

  function resetDraft() {
    setSelectedOption(null);
    setText("");
    setCode("");
    setRunResult(null);
    setLastResult(null);
  }

  async function submitCurrent() {
    if (!attemptId || !question || busy) return;
    setBusy(true);
    setError("");
    try {
      let answer: Record<string, unknown>;
      if (OBJECTIVE.has(question.question_type) && question.question_type !== "code_output") {
        answer = { option_index: selectedOption };
      } else if (question.question_type === "code_output") {
        answer = { text };
      } else if (question.question_type === "sql_query") {
        answer = { sql: text };
      } else if (question.question_type === "coding") {
        const res = await assessmentApi.submitCode(attemptId, question.id, code);
        setLastResult(res);
        await refreshState();
        return;
      } else {
        answer = { text };
      }
      const res = await assessmentApi.answer(attemptId, question.id, answer);
      setLastResult(res);
      await refreshState();
    } catch {
      setError("Submission failed - it may already be answered or the time is up.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshState() {
    if (!attemptId) return;
    try {
      const st = await assessmentApi.state(attemptId);
      setState(st);
      if (st.status !== "in_progress") void finalize();
    } catch {
      /* keep current state */
    }
  }

  async function runCode() {
    if (!attemptId || !question) return;
    setBusy(true);
    setRunResult(null);
    try {
      setRunResult(await assessmentApi.runCode(attemptId, question.id, code));
    } catch {
      setError("Code execution failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !state) {
    return (
      <div className="mx-auto max-w-xl rounded-xl bg-red-50 p-6 text-center text-sm text-red-600">{error}</div>
    );
  }
  if (!state || !question) {
    return <LoadingSpinner size="lg" className="mt-20" />;
  }

  const answeredCount = Object.keys(state.answered || {}).length;
  const total = state.questions.length;
  const answered = isAnswered(question.id);

  return (
    <div className="space-y-4">
      {/* Header: title, progress, timer */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
              {(attempt?.sections ?? []).slice(0, 3).join(" · ")}
            </p>
            <h1 className="text-lg font-bold text-gray-900">{answeredCount}/{total} answered</h1>
          </div>
          <div className={`rounded-lg px-3 py-1.5 font-mono text-lg font-bold ${secondsLeft !== null && secondsLeft < 120 ? "bg-red-50 text-red-600" : "bg-gray-100 text-gray-700"}`}>
            {secondsLeft === null ? "--:--" : fmtTime(secondsLeft)}
          </div>
          <button
            onClick={() => { void finalize(); }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Finish & Submit
          </button>
        </div>
        <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-primary-500 transition-all"
            style={{ width: `${total ? (answeredCount / total) * 100 : 0}%` }} />
        </div>
        <ul className="mt-3 hidden list-inside list-disc text-xs text-gray-400 md:block">
          {(attempt?.instructions ?? []).slice(0, 3).map((ins) => <li key={ins}>{ins}</li>)}
        </ul>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Question card */}
      <QuestionCard
        question={question}
        index={idx}
        total={total}
        selectedOption={selectedOption}
        onSelect={(i) => !answered && setSelectedOption(i)}
        text={text}
        onText={(v) => !answered && setText(v)}
        code={code}
        onCode={(v) => setCode(v)}
        runResult={runResult}
        onRun={runCode}
        onSubmit={() => void submitCurrent()}
        lastResult={lastResult}
        answered={answered}
        busy={busy}
      />

      {/* Footer navigation */}
      <div className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <button
          onClick={() => { resetDraft(); setIdx((i) => Math.max(i - 1, 0)); }}
          disabled={idx === 0}
          className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
        >
          Previous
        </button>
        <div className="flex flex-wrap justify-center gap-1.5">
          {state.questions.map((q, i) => (
            <button
              key={q.id}
              onClick={() => { resetDraft(); setIdx(i); }}
              className={`h-8 w-8 rounded-lg text-xs font-semibold ${
                i === idx ? "bg-primary-600 text-white"
                  : isAnswered(q.id) ? "bg-green-100 text-green-700"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>
        {idx < total - 1 ? (
          <button
            onClick={() => { resetDraft(); setIdx((i) => Math.min(i + 1, total - 1)); }}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Next
          </button>
        ) : (
          <button
            onClick={() => { void finalize(); }}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Finish
          </button>
        )}
        </div>
      </div>
  );
}

interface CardProps {
  question: QuestionPublic;
  index: number;
  total: number;
  selectedOption: number | null;
  onSelect: (i: number) => void;
  text: string;
  onText: (v: string) => void;
  code: string;
  onCode: (v: string) => void;
  runResult: CodeRunResponse | null;
  onRun: () => void;
  onSubmit: () => void;
  lastResult: AnswerResultResponse | null;
  answered: boolean;
  busy: boolean;
}

function QuestionCard(p: CardProps) {
  const q = p.question;
  const isObjectiveMcq = OBJECTIVE.has(q.question_type) && q.question_type !== "code_output";
  const isCodeOutput = q.question_type === "code_output";
  const isSql = q.question_type === "sql_query";
  const isCoding = q.question_type === "coding";
  const isSubjective = SUBJECTIVE.has(q.question_type);

  return (
    <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700">
          Q{p.index + 1} of {p.total}
        </span>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600">
          {q.question_type.replace(/_/g, " ")}
        </span>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium capitalize text-gray-600">
          {q.difficulty}
        </span>
        <span className="text-xs text-gray-400">{q.points} pts · {q.section}</span>
      </div>

      <p className="whitespace-pre-wrap text-base font-medium text-gray-900">{q.question_text}</p>

      {q.code_snippet && (
        <pre className="overflow-x-auto rounded-lg bg-gray-950 p-4 text-xs leading-relaxed text-green-200">
          {q.code_snippet}
        </pre>
      )}

      {isObjectiveMcq && (
        <div className="space-y-2">
          {q.options.map((opt, i) => {
            const chosen = p.selectedOption === i;
            return (
              <label key={i} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition ${
                chosen ? "border-primary-500 bg-primary-50" : "border-gray-200 hover:bg-gray-50"
              }`}>
                <input type="radio" className="h-4 w-4" checked={chosen}
                  onChange={() => p.onSelect(i)} disabled={p.answered} />
                <span className="font-mono text-xs text-gray-400">{String.fromCharCode(65 + i)}.</span>
                <span>{opt}</span>
              </label>
            );
          })}
        </div>
      )}

      {(isCodeOutput || isSubjective || isSql) && (
        <textarea
          value={p.text}
          onChange={(e) => p.onText(e.target.value)}
          disabled={p.answered}
          rows={isSubjective ? 7 : 3}
          placeholder={
            isCodeOutput ? "Write the exact program output..."
              : isSql ? "Write your SQL query..." : "Type your answer..."
          }
          className="w-full rounded-lg border border-gray-300 p-3 font-mono text-sm focus:border-primary-500 focus:outline-none disabled:bg-gray-50"
        />
      )}

      {isSql && q.schema_sql && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-400">Schema</p>
          <pre className="overflow-x-auto rounded-lg bg-gray-50 p-3 text-xs text-gray-700">{q.schema_sql}</pre>
        </div>
      )}

      {isCoding && (
        <div className="space-y-3">
          {q.starter_code && (
            <button
              onClick={() => p.onCode(p.code || q.starter_code!)}
              className="text-xs font-medium text-primary-600 hover:underline"
            >
              Load starter code
            </button>
          )}
          <textarea
            value={p.code}
            onChange={(e) => p.onCode(e.target.value)}
            rows={12}
            spellCheck={false}
            placeholder="# Write your solution here"
            className="w-full rounded-lg border border-gray-300 bg-gray-950 p-4 font-mono text-sm text-green-100 focus:border-primary-500 focus:outline-none"
          />
          <button
            onClick={p.onRun}
            disabled={p.busy || !p.code.trim()}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-40"
          >
            {p.busy ? "Running..." : "Run tests"}
          </button>
        </div>
      )}

      {p.runResult && (
        <div className={`rounded-lg border p-4 text-sm ${p.runResult.ok ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}`}>
          <p className="font-semibold">
            {p.runResult.passed_count}/{p.runResult.total_count} test cases passed
            {p.runResult.timed_out ? " · TIME LIMIT EXCEEDED" : ""}
          </p>
          {p.runResult.stderr && (
            <pre className="mt-2 overflow-x-auto text-xs text-red-600">{p.runResult.stderr}</pre>
          )}
        </div>
      )}

      {!p.answered && (
        <button
          onClick={p.onSubmit}
          disabled={p.busy || (isObjectiveMcq && p.selectedOption === null) ||
            ((isCodeOutput || isSubjective || isSql) && !p.text.trim()) ||
            (isCoding && !p.code.trim())}
          className="w-full rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-40"
        >
          {isCoding ? "Submit solution" : "Submit answer"}
        </button>
      )}

      {p.lastResult && (
        <div className={`rounded-lg border p-4 ${
          p.lastResult.evaluation.is_correct === true
            ? "border-green-200 bg-green-50"
            : p.lastResult.evaluation.is_correct === false
              ? "border-red-200 bg-red-50"
              : "border-blue-200 bg-blue-50"
        }`}>
          <p className="text-sm font-semibold">Score: {p.lastResult.evaluation.score}/100</p>
          {p.lastResult.explanation && (
            <p className="mt-1 text-xs text-gray-600">Explanation: {p.lastResult.explanation}</p>
          )}
          {p.lastResult.evaluation.feedback && (
            <p className="mt-1 text-xs text-gray-600">{p.lastResult.evaluation.feedback}</p>
          )}
        </div>
      )}
    </div>
  );
}

