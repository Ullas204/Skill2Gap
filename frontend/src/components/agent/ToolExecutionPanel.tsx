import type { ToolExecutionResponse } from "../../types/agent";

interface Props {
  executions: ToolExecutionResponse[];
}

export function ToolExecutionPanel({ executions }: Props) {
  if (executions.length === 0) return null;

  return (
    <div className="border-t bg-gray-50 p-3">
      <div className="text-xs text-gray-500 font-semibold mb-2">Tool Executions</div>
      <div className="space-y-2">
        {executions.map((te) => (
          <div key={te.id} className="bg-white rounded border border-gray-200 p-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    te.status === "completed" ? "bg-green-500" : te.status === "failed" ? "bg-red-500" : "bg-yellow-500"
                  }`}
                />
                <span className="text-xs font-medium text-gray-700">{te.tool_name}</span>
              </div>
              <span className="text-xs text-gray-400">{te.execution_time_ms}ms</span>
            </div>
            {te.status === "completed" && te.result && (
              <pre className="text-xs text-gray-500 mt-1 max-h-20 overflow-y-auto">
                {JSON.stringify(te.result, null, 2).slice(0, 300)}
              </pre>
            )}
            {te.status === "failed" && te.error && (
              <div className="text-xs text-red-500 mt-1">{te.error}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
