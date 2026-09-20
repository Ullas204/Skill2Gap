import { useEffect, useCallback } from "react";
import { useAgent } from "../../hooks/useAgent";
import { ChatMessageList } from "../../components/agent/ChatMessageList";
import { ChatInput } from "../../components/agent/ChatInput";
import { SuggestedPrompts } from "../../components/agent/SuggestedPrompts";
import { ToolExecutionPanel } from "../../components/agent/ToolExecutionPanel";
import { ConversationSidebar } from "../../components/agent/ConversationSidebar";
import { AgentInfoPanel } from "../../components/agent/AgentInfoPanel";
import { useAuth } from "../../hooks/useAuth";

export function AIChat() {
  const { user } = useAuth();
  const roles = user?.roles || ["candidate"];
  const {
    messages,
    conversations,
    agents,
    providers,
    activeConversationId,
    isLoading,
    toolExecutions,
    agentUsed,
    processingTimeMs,
    providerUsed,
    sendMessage,
    loadConversations,
    loadConversation,
    loadAgents,
    loadProviders,
    startNewConversation,
    clearChat,
    suggestedPrompts,
    retryLastMessage,
  } = useAgent(roles);

  useEffect(() => {
    loadConversations();
    loadAgents();
    loadProviders();
  }, [loadConversations, loadAgents, loadProviders]);

  const handleSend = useCallback(
    (message: string) => {
      sendMessage(message);
      setTimeout(() => loadConversations(), 500);
    },
    [sendMessage, loadConversations],
  );

  const handleExport = useCallback(() => {
    const text = messages
      .map((m) => {
        const role = m.role === "user" ? "You" : "AI";
        return `[${role}]: ${m.content}`;
      })
      .join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat-export-${new Date().toISOString().slice(0, 10)}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [messages]);

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-white">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={loadConversation}
        onNew={startNewConversation}
      />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="border-b bg-white px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-800">AI HR Intelligence Assistant</h1>
            <p className="text-xs text-gray-500">
              Ask questions about recruitment, candidates, analytics, and more
              {providerUsed && (
                <span className="ml-2 text-indigo-500 font-medium">via {providerUsed}</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {agentUsed && (
              <span className="text-xs bg-indigo-100 text-indigo-700 rounded-full px-2.5 py-1 font-medium capitalize">
                {agentUsed.replace("_", " ")} Agent
              </span>
            )}
            <button
              onClick={retryLastMessage}
              disabled={isLoading || messages.length === 0}
              className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 px-2 py-1 rounded hover:bg-gray-100"
              title="Retry last message"
            >
              Retry
            </button>
            <button
              onClick={handleExport}
              disabled={messages.length === 0}
              className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 px-2 py-1 rounded hover:bg-gray-100"
              title="Export conversation"
            >
              Export
            </button>
            <button
              onClick={clearChat}
              disabled={messages.length === 0}
              className="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 px-2 py-1 rounded hover:bg-gray-100"
              title="Clear chat"
            >
              Clear
            </button>
          </div>
        </div>

        <ChatMessageList messages={messages} isLoading={isLoading} />

        {messages.length <= 1 && (
          <SuggestedPrompts prompts={suggestedPrompts} onSelect={handleSend} />
        )}

        {toolExecutions.length > 0 && (
          <ToolExecutionPanel executions={toolExecutions} />
        )}

        <ChatInput onSend={handleSend} isLoading={isLoading} />
      </div>

      <AgentInfoPanel
        agents={agents}
        toolExecutions={toolExecutions}
        agentUsed={agentUsed}
        processingTimeMs={processingTimeMs}
        providers={providers}
      />
    </div>
  );
}
