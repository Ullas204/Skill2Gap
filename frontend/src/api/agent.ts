import apiClient from "./client";
import type { ChatResponse, ConversationDetail, AgentInfo, WorkflowTemplate, AgentActivity, AgentStats, ProviderInfo } from "../types/agent";

export async function sendChatMessage(
  message: string,
  conversationId?: string,
): Promise<ChatResponse> {
  const { data } = await apiClient.post("/agent/chat", {
    message,
    conversation_id: conversationId || null,
    stream: false,
  });
  return data;
}

export async function sendChatMessageStream(
  message: string,
  conversationId?: string,
  onChunk?: (chunk: string) => void,
  onMetadata?: (meta: { conversation_id: string; agent_type: string; citations: unknown[] }) => void,
  onDone?: (data: { content: string; agent_type: string; citations: unknown[] }) => void,
  onError?: (error: string) => void,
): Promise<void> {
  const token = localStorage.getItem("access_token") || "";
  const response = await fetch("/api/v1/agent/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, conversation_id: conversationId || null, stream: true }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => "Request failed");
    onError?.(errText);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    onError?.("No response stream");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          switch (event.type) {
            case "metadata":
              onMetadata?.(event);
              break;
            case "delta":
              onChunk?.(event.content || "");
              break;
            case "done":
              onDone?.(event);
              break;
            case "error":
              onError?.(event.content || "Unknown error");
              break;
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  } catch (err) {
    onError?.("Stream interrupted");
  } finally {
    reader.releaseLock();
  }
}

export async function getConversations(): Promise<{ conversations: Array<{ id: string; title?: string; agent_type?: string; created_at: string; updated_at: string }> }> {
  const { data } = await apiClient.get("/agent/conversations");
  return data;
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const { data } = await apiClient.get(`/agent/conversations/${conversationId}`);
  return data;
}

export async function getAgents(): Promise<{ agents: AgentInfo[] }> {
  const { data } = await apiClient.get("/agent/agents");
  return data;
}

export async function getTools(): Promise<{ tools: string[] }> {
  const { data } = await apiClient.get("/agent/tools");
  return data;
}

export async function getProviders(): Promise<{ providers: ProviderInfo[] }> {
  try {
    const { data } = await apiClient.get("/agent/providers");
    return data;
  } catch {
    return { providers: [] };
  }
}

export async function getWorkflows(): Promise<{ workflows: WorkflowTemplate[] }> {
  const { data } = await apiClient.get("/agent/workflows");
  return data;
}

export async function getActivityLogs(): Promise<{ activity: AgentActivity[] }> {
  const { data } = await apiClient.get("/agent/activity");
  return data;
}

export async function getAgentStats(): Promise<AgentStats> {
  const { data } = await apiClient.get("/agent/stats");
  return data;
}

export async function createWorkflow(name: string, steps: Array<{ name: string; tool_name: string; confirmation_required?: boolean }>): Promise<{ workflow_id: string; name: string; status: string; steps_count: number }> {
  const { data } = await apiClient.post("/agent/workflows", { name, description: name, steps });
  return data;
}

export async function executeWorkflow(workflowId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post(`/agent/workflows/${workflowId}/execute`);
  return data;
}

export async function generateReport(reportType: string, title?: string, exportFormat?: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post("/agent/reports/generate", {
    report_type: reportType,
    title,
    export_format: exportFormat || "pdf",
  });
  return data;
}

export async function exportReport(reportType: string, format: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post("/agent/reports/export", {
    report_type: reportType,
    export_format: format,
  });
  return data;
}
