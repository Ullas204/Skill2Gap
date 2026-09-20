import type { Conversation } from "../../types/agent";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function ConversationSidebar({ conversations, activeId, onSelect, onNew }: Props) {
  return (
    <div className="w-64 border-r bg-gray-50 flex flex-col h-full">
      <div className="p-3 border-b">
        <button
          onClick={onNew}
          className="w-full bg-indigo-600 text-white text-sm rounded-lg px-3 py-2 hover:bg-indigo-700 transition-colors font-medium"
        >
          + New Chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.length === 0 ? (
          <div className="text-xs text-gray-400 text-center mt-8">No conversations yet</div>
        ) : (
          conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={`w-full text-left rounded-lg px-3 py-2 text-sm transition-colors ${
                activeId === c.id
                  ? "bg-indigo-100 text-indigo-700 font-medium"
                  : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <div className="truncate">{c.title || "New Conversation"}</div>
              <div className="text-xs text-gray-400 mt-0.5">
                {c.agent_type && <span className="capitalize">{c.agent_type} Agent</span>}
                {" \u00b7 "}
                {new Date(c.updated_at).toLocaleDateString()}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
