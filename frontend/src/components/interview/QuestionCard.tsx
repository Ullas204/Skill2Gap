import { CATEGORY_LABELS, DIFFICULTY_COLORS } from "../../types/interview";
import type { InterviewQuestion } from "../../types/interview";

export function QuestionCard({
  question,
  index,
}: {
  question: InterviewQuestion;
  index: number;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600">
              Q{index + 1}
            </span>
            <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${DIFFICULTY_COLORS[question.difficulty] || "bg-gray-100 text-gray-600"}`}>
              {question.difficulty}
            </span>
            <span className="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700">
              {CATEGORY_LABELS[question.category as keyof typeof CATEGORY_LABELS] || question.category}
            </span>
          </div>
          <p className="text-sm leading-relaxed text-gray-900">{question.question_text}</p>
        </div>
      </div>
    </div>
  );
}
