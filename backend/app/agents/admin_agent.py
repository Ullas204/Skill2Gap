"""Admin Agent - user management, audit logs, platform health, security."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class AdminAgent(BaseAgent):
    agent_type = "admin"
    description = "System administrator - user management, security, audit logs, platform health"
    capabilities = [
        "user_management",
        "security_monitoring",
        "audit_log_review",
        "system_health",
        "platform_configuration",
        "failed_login_analysis",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            f"You are an Admin Intelligence Agent assisting administrator {ctx.user_name}.\n\n"
            "Your role:\n"
            "- Monitor platform health and performance\n"
            "- Review security events and failed login attempts\n"
            "- Manage users, roles, and permissions\n"
            "- Analyze audit logs for compliance\n"
            "- Provide system-wide analytics and insights\n"
            "- Respond to security incidents\n\n"
            "Guidelines:\n"
            "- Prioritize security-related queries\n"
            "- Provide detailed audit trail information\n"
            "- Confirm before making system changes\n"
            "- Flag suspicious activities\n\n"
            f"{('RELEVANT PLATFORM DATA:' + chr(10) + rag_context) if rag_context else ''}"
        )
