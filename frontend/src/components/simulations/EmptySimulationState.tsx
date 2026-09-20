interface EmptySimulationStateProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptySimulationState({
  title,
  description,
  actionLabel,
  onAction,
}: EmptySimulationStateProps) {
  return (
    <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center">
      <p className="text-gray-500">{title}</p>
      <p className="mt-1 text-sm text-gray-400">{description}</p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="mt-4 text-sm font-medium text-primary-600 hover:text-primary-700"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}