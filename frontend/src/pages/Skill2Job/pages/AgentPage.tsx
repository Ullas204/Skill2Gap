import { AIChat } from "../../agent/AIChat";

export default function AgentPage() {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-primary-100 bg-gradient-to-br from-primary-50 to-indigo-50 p-5">
        <h2 className="text-lg font-bold text-gray-900">AI Career Agent</h2>
        <p className="mt-1 text-sm text-gray-600">
          Ask anything about your career: which roles fit you, what skills to learn next, how to
          close gaps, or how to present your experience. Your conversations reuse the existing
          multi-provider agent infrastructure.
        </p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
        <AIChat />
      </div>
    </div>
  );
}