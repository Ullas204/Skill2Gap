export interface Citation {
  source_type: string;
  source_id: string;
  title: string;
  excerpt: string;
  relevance_score: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system" | "tool_call" | "tool_result";
  content: string;
  agent_type?: string;
  citations?: Citation[];
  timestamp?: string;
  tool_calls?: ToolCallInfo[];
  isStreaming?: boolean;
}

export interface ToolCallInfo {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed";
  result?: Record<string, unknown>;
  execution_time_ms?: number;
}

export interface ChatResponse {
  conversation_id: string;
  message: ChatMessage;
  tool_executions: ToolExecutionResponse[];
  agent_used: string;
  processing_time_ms: number;
  provider_used: string;
  tokens_used: number;
}

export interface ToolExecutionResponse {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed";
  error?: string;
  execution_time_ms: number;
}

export interface Conversation {
  id: string;
  title?: string;
  agent_type?: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface AgentInfo {
  type: string;
  description: string;
  capabilities: string[];
}

export interface ProviderInfo {
  name: string;
  model: string;
  status: string;
  success_rate: number;
  avg_latency_ms: number;
  total_requests: number;
}

export interface WorkflowTemplate {
  name: string;
  description: string;
  steps: string[];
}

export interface AgentActivity {
  id: string;
  agent_type: string;
  action: string;
  details?: Record<string, unknown>;
  tokens_used: number;
  latency_ms: number;
  success: boolean;
  created_at: string;
}

export interface AgentStats {
  total_actions: number;
  total_tokens: number;
  avg_latency_ms: number;
}

export interface StreamEvent {
  type: "metadata" | "start" | "delta" | "done" | "error";
  content?: string;
  conversation_id?: string;
  agent_type?: string;
  citations?: Citation[];
}
