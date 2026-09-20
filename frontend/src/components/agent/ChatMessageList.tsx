import { useRef, useEffect, useState } from "react";
import type { ChatMessage } from "../../types/agent";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function ChatMessageList({ messages, isLoading }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="text-5xl mb-4">&#x1F916;</div>
          <h3 className="text-lg font-semibold text-gray-600 mb-2">AI HR Intelligence Assistant</h3>
          <p className="text-sm">Ask me anything about recruitment, candidates, interviews, or analytics.</p>
          <p className="text-xs text-gray-400 mt-2">Powered by multi-LLM routing with automatic fallback</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {isLoading && !messages.some((m) => m.isStreaming) && (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold">AI</div>
          <div className="bg-gray-100 rounded-lg px-4 py-3">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function renderMarkdown(text: string): string {
  let html = text;
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre class="bg-gray-800 text-gray-100 rounded-lg p-3 text-xs overflow-x-auto my-2"><code>$2</code></pre>');
  html = html.replace(/`([^`]+)`/g, '<code class="bg-gray-100 text-gray-800 rounded px-1 py-0.5 text-xs">$1</code>');
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/\n/g, "<br/>");
  return html;
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const agentLabel: Record<string, string> = {
    candidate: "Career Agent",
    recruiter: "Recruiter Agent",
    hr: "HR Agent",
    admin: "Admin Agent",
    resume: "Resume Agent",
    interview: "Interview Agent",
    analytics: "Analytics Agent",
    fairness: "Fairness Agent",
    report: "Report Agent",
    job_matching: "Matching Agent",
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex items-start gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
          {message.agent_type ? (agentLabel[message.agent_type] || "AI").charAt(0) : "AI"}
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? "order-first" : ""}`}>
        {!isUser && message.agent_type && (
          <div className="text-xs text-indigo-600 font-semibold mb-1">{agentLabel[message.agent_type] || "AI Agent"}</div>
        )}
        <div
          className={`rounded-lg px-4 py-2 text-sm ${
            isUser
              ? "bg-indigo-600 text-white rounded-br-none"
              : "bg-gray-100 text-gray-800 rounded-bl-none"
          } ${message.isStreaming ? "border-l-2 border-indigo-300 animate-pulse" : ""}`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{message.content}</span>
          ) : (
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 bg-indigo-500 animate-pulse ml-0.5 align-middle" />
          )}
        </div>
        {!isUser && !message.isStreaming && message.content && (
          <div className="flex items-center gap-2 mt-1">
            <button
              onClick={handleCopy}
              className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
              title="Copy response"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        )}
        {message.citations && message.citations.length > 0 && (
          <div className="mt-2 space-y-1">
            {message.citations.map((c, ci) => (
              <div key={ci} className="text-xs bg-blue-50 text-blue-700 rounded px-2 py-1 border border-blue-100">
                <span className="font-semibold">{c.source_type}:</span> {c.title}
                <span className="text-blue-400 ml-1">({(c.relevance_score * 100).toFixed(0)}% match)</span>
              </div>
            ))}
          </div>
        )}
        {message.timestamp && (
          <div className={`text-xs text-gray-400 mt-1 ${isUser ? "text-right" : ""}`}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">U</div>
      )}
    </div>
  );
}
