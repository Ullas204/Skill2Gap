"""Notification helpers for firing Celery email tasks."""
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

ROLE_LABELS = {
    "hr_manager": "HR Manager",
    "organization_admin": "Organization Admin",
    "recruiter": "Recruiter",
    "candidate": "Candidate",
    "super_admin": "Super Admin",
    "admin": "Platform Admin",
}


def _celery_available() -> bool:
    try:
        import redis as _redis
        settings = get_settings()
        r = _redis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


def _send_invitation_email_sync(
    to_email: str,
    invited_by_name: str,
    organization_name: str,
    role_label: str,
    accept_url: str,
    expires_at_str: str,
    app_name: str,
) -> dict:
    from app.services.email_service import EmailService

    email_svc = EmailService()
    subject = f"You've been invited to join {organization_name}"
    html_body = email_svc.render_template(
        "invitation_email.html",
        invited_by_name=invited_by_name,
        organization_name=organization_name,
        role_label=role_label,
        accept_url=accept_url,
        expires_at=expires_at_str,
        app_name=app_name,
    )
    return email_svc.send_html(to_email=to_email, subject=subject, html_body=html_body)


def queue_invitation_email(
    to_email: str,
    invited_by_name: str,
    organization_name: str,
    role: str,
    raw_token: str,
    expires_at_str: str,
) -> dict:
    settings = get_settings()
    accept_url = f"{settings.frontend_base_url}/invite/{raw_token}"
    role_label = ROLE_LABELS.get(role, role)
    app_name = settings.app_name

    if not _celery_available():
        logger.info(
            "Celery broker unavailable — sending invitation email synchronously (to=%s, org=%s)",
            to_email,
            organization_name,
        )
        try:
            result = _send_invitation_email_sync(
                to_email=to_email,
                invited_by_name=invited_by_name,
                organization_name=organization_name,
                role_label=role_label,
                accept_url=accept_url,
                expires_at_str=expires_at_str,
                app_name=app_name,
            )
            return {
                "status": result.get("status", "sent"),
                "reason": result.get("reason"),
            }
        except Exception:
            logger.exception("Synchronous invitation email failed for %s", to_email)
            return {"status": "error", "reason": "sync_send_failed"}

    try:
        from app.workers.tasks import send_invitation_email

        result = send_invitation_email.delay(
            to_email=to_email,
            invited_by_name=invited_by_name,
            organization_name=organization_name,
            role_label=role_label,
            accept_url=accept_url,
            expires_at=expires_at_str,
            app_name=app_name,
        )
        logger.info(
            "Invitation email queued: to=%s task_id=%s",
            to_email,
            result.id,
        )
        return {"status": "queued", "task_id": result.id}
    except Exception:
        logger.exception("Failed to queue invitation email to %s", to_email)
        return {"status": "queue_error"}
