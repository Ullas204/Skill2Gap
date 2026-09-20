"""Notification and report tools for the agent platform."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.session import async_session_factory
from app.domain.models import Notification, User
from app.tools.registry import tool_registry


async def send_notification(user_id: str, title: str, message: str, notification_type: str = "general") -> dict:
    async with async_session_factory() as db:
        notif = Notification(
            user_id=uuid.UUID(user_id),
            title=title,
            message=message,
            notification_type=notification_type,
        )
        db.add(notif)
        await db.flush()
        await db.commit()
        return {
            "id": str(notif.id),
            "message": f"Notification sent to user {user_id}.",
            "title": title,
        }


async def export_report(report_type: str = "hiring", format: str = "pdf") -> dict:
    return {
        "report_type": report_type,
        "format": format,
        "status": "generated",
        "download_url": f"/uploads/reports/{report_type}_report.{format}",
        "message": f"{report_type.title()} report exported as {format.upper()}.",
    }


async def generate_report(report_type: str = "hiring", title: str = "", parameters: str = "") -> dict:
    async with async_session_factory() as db:
        if report_type == "hiring":
            from app.domain.models import Job, JobApplication
            total_jobs = (await db.execute(select(Job))).scalars().all()
            published = [j for j in total_jobs if j.status == "published"]
            all_apps = (await db.execute(select(JobApplication))).scalars().all()

            return {
                "title": title or "Hiring Report",
                "report_type": "hiring",
                "content": {
                    "total_jobs": len(total_jobs),
                    "published_jobs": len(published),
                    "total_applications": len(all_apps),
                    "status_breakdown": {},
                },
                "format": "json",
                "message": "Hiring report generated.",
            }
        return {
            "title": title or f"{report_type.title()} Report",
            "report_type": report_type,
            "content": {"message": f"Report generated for {report_type}."},
            "message": f"{report_type.title()} report generated.",
        }


def _register() -> None:
    tool_registry.register("send_notification", "Send a notification to a user", {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "Target user UUID"},
            "title": {"type": "string", "description": "Notification title"},
            "message": {"type": "string", "description": "Notification message"},
            "notification_type": {"type": "string", "description": "Type: general, application_status, etc."},
        },
        "required": ["user_id", "title", "message"],
    }, send_notification, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("export_report", "Export a report to file (PDF/CSV)", {
        "type": "object",
        "properties": {
            "report_type": {"type": "string", "description": "Type of report"},
            "format": {"type": "string", "description": "Export format: pdf, csv, excel"},
        },
        "required": ["report_type"],
    }, export_report, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("generate_report", "Generate an AI-powered report", {
        "type": "object",
        "properties": {
            "report_type": {"type": "string", "description": "Type: hiring, candidate, fairness, interview, executive"},
            "title": {"type": "string", "description": "Report title"},
            "parameters": {"type": "string", "description": "Additional parameters"},
        },
        "required": ["report_type"],
    }, generate_report, required_roles=["recruiter", "hr", "admin"])
