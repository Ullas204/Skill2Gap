export function InterviewTimeline({
  steps,
  currentStatus,
}: {
  steps: string[];
  currentStatus: string;
}) {
  const currentIdx = steps.findIndex((s) => s === currentStatus);

  return (
    <div className="flex items-center">
      {steps.map((step, idx) => {
        const isCompleted = idx < currentIdx;
        const isCurrent = idx === currentIdx;
        return (
          <div key={step} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${
                  isCompleted
                    ? "bg-green-500 text-white"
                    : isCurrent
                      ? "bg-primary-500 text-white ring-2 ring-primary-200"
                      : "bg-gray-200 text-gray-500"
                }`}
              >
                {isCompleted ? "✓" : idx + 1}
              </div>
              <span className="mt-1 text-[10px] text-gray-500 capitalize">{step.replace("_", " ")}</span>
            </div>
            {idx < steps.length - 1 && (
              <div className={`mx-1 h-0.5 w-8 ${isCompleted ? "bg-green-500" : "bg-gray-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
