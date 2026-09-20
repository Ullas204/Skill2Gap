interface Props {
  prompts: string[];
  onSelect: (prompt: string) => void;
}

export function SuggestedPrompts({ prompts, onSelect }: Props) {
  if (prompts.length === 0) return null;

  return (
    <div className="px-4 pb-2">
      <div className="text-xs text-gray-500 mb-2 font-medium">Suggested</div>
      <div className="flex flex-wrap gap-2">
        {prompts.map((p, i) => (
          <button
            key={i}
            onClick={() => onSelect(p)}
            className="text-xs bg-indigo-50 text-indigo-700 rounded-full px-3 py-1.5 hover:bg-indigo-100 transition-colors border border-indigo-100"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
