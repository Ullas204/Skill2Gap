import type { AgentInfo, ToolExecutionResponse, ProviderInfo } from "../../types/agent";

interface Props {
  agents: AgentInfo[];
  toolExecutions: ToolExecutionResponse[];
  agentUsed: string;
  processingTimeMs: number;
  providers: ProviderInfo[];
}

export function AgentInfoPanel({ agents, toolExecutions, agentUsed, processingTimeMs, providers }: Props) {
  return (
    <div className="w-72 border-l bg-gray-50 flex flex-col h-full overflow-y-auto">
      <div className="p-3 border-b">
        <h3 className="text-sm font-semibold text-gray-700">Agent Status</h3>
      </div>

      {agentUsed && (
        <div className="p-3 border-b">
          <div className="text-xs text-gray-500 mb-1">Active Agent</div>
          <div className="bg-indigo-50 text-indigo-700 rounded-lg px-3 py-2 text-sm font-medium capitalize">
            {agentUsed.replace("_", " ")} Agent
          </div>
          {processingTimeMs > 0 && (
            <div className="text-xs text-gray-400 mt-1">Response time: {processingTimeMs}ms</div>
          )}
        </div>
      )}

      {providers.length > 0 && (
        <div className="p-3 border-b">
          <div className="text-xs text-gray-500 mb-2">LLM Providers</div>
          <div className="space-y-1.5">
            {providers.map((p) => (
              <div key={p.name} className="bg-white rounded border border-gray-200 px-2 py-1.5">
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${
                    p.status === "healthy" ? "bg-green-500" : p.status === "degraded" ? "bg-yellow-500" : "bg-red-500"
                  }`} />
                  <span className="text-xs font-medium capitalize">{p.name}</span>
                  <span className="text-xs text-gray-400 ml-auto">{(p.success_rate * 100).toFixed(0)}%</span>
                </div>
                <div className="text-xs text-gray-400 mt-0.5">{p.model}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {toolExecutions.length > 0 && (
        <div className="p-3 border-b">
          <div className="text-xs text-gray-500 mb-2">Tools Used ({toolExecutions.length})</div>
          <div className="space-y-1.5">
            {toolExecutions.map((te) => (
              <div key={te.id} className="bg-white rounded border border-gray-200 px-2 py-1.5">
                <div className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${te.status === "completed" ? "bg-green-500" : "bg-red-500"}`} />
                  <span className="text-xs font-medium">{te.tool_name}</span>
                </div>
                <div className="text-xs text-gray-400">{te.execution_time_ms}ms</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="p-3">
        <div className="text-xs text-gray-500 mb-2">Available Agents ({agents.length})</div>
        <div className="space-y-2">
          {agents.map((a) => (
            <div key={a.type} className="bg-white rounded border border-gray-200 p-2">
              <div className="text-xs font-semibold text-gray-700 capitalize">{a.type.replace("_", " ")}</div>
              <div className="text-xs text-gray-500 mt-0.5">{a.description}</div>
              <div className="flex flex-wrap gap-1 mt-1.5">
                {a.capabilities.slice(0, 3).map((cap) => (
                  <span key={cap} className="text-xs bg-gray-100 text-gray-600 rounded px-1.5 py-0.5">
                    {cap.replace(/_/g, " ")}
                  </span>
                ))}
                {a.capabilities.length > 3 && (
                  <span className="text-xs text-gray-400">+{a.capabilities.length - 3}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
