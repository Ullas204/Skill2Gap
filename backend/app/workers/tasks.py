import asyncio
import logging
import smtplib
import uuid

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="send_email", bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body: str) -> dict:
    from app.services.email_service import EmailService

    email_svc = EmailService()
    try:
        result = email_svc.send_html(to_email=to, subject=subject, html_body=body)
        return {"to": to, "subject": subject, "status": result.get("status", "sent")}
    except smtplib.SMTPException as exc:
        logger.warning("SMTP error sending email to %s: %s", to, exc)
        raise self.retry(exc=exc, countdown=30)
    except Exception as exc:
        logger.exception("Failed to send email to %s", to)
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(name="run_simulation", bind=True)
def run_simulation(self, scenario_id: str, execution_id: str) -> dict:
    """Execute one simulation run to completion.

    The engine itself is idempotent for completed/cancelled/running executions
    and records failure + audit on its own, so the worker does not retry: a
    transient error is surfaced on the execution row and the recruiter can
    simply re-run the scenario.
    """
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import async_session_factory
    from app.services.simulation.execution_service import SimulationExecutionService

    async def _run() -> None:
        async with async_session_factory() as session:
            service = SimulationExecutionService(session)
            execution = await service.execute(uuid.UUID(execution_id))
            logger.info(
                "Simulation worker finished: execution=%s status=%s",
                execution.id, execution.status,
            )

    try:
        _run_async(_run())
        return {
            "scenario_id": scenario_id,
            "execution_id": execution_id,
            "status": "completed",
        }
    except Exception as exc:
        logger.exception("Simulation run failed for execution %s", execution_id)
        return {
            "scenario_id": scenario_id,
            "execution_id": execution_id,
            "status": "error",
            "error": str(exc)[:1000],
        }


def _run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="process_resume", bind=True, max_retries=2, default_retry_delay=60)
def process_resume(self, resume_id: str) -> dict:
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import async_session_factory
    from app.services.candidate.resume import ResumeService

    async def _run() -> None:
        async with async_session_factory() as session:
            service = ResumeService(session)
            await service.process_resume(uuid.UUID(resume_id))

    try:
        _run_async(_run())
        return {"resume_id": resume_id, "status": "parsed"}
    except Exception as exc:
        logger.exception("Resume processing failed for %s", resume_id)
        raise self.retry(exc=exc)


@celery_app.task(name="send_invitation_email", bind=True, max_retries=3, default_retry_delay=60)
def send_invitation_email(
    self,
    to_email: str,
    invited_by_name: str,
    organization_name: str,
    role_label: str,
    accept_url: str,
    expires_at: str,
    app_name: str = "AI Hiring Copilot",
) -> dict:
    from app.services.email_service import EmailService

    email_svc = EmailService()

    subject = f"You've been invited to join {organization_name}"
    try:
        html_body = email_svc.render_template(
            "invitation_email.html",
            invited_by_name=invited_by_name,
            organization_name=organization_name,
            role_label=role_label,
            accept_url=accept_url,
            expires_at=expires_at,
            app_name=app_name,
        )
    except Exception:
        logger.exception("Failed to render invitation email template for %s", to_email)
        return {"to": to_email, "status": "template_error"}

    try:
        result = email_svc.send_html(to_email=to_email, subject=subject, html_body=html_body)
        return {"to": to_email, "status": result.get("status", "sent")}
    except smtplib.SMTPException as exc:
        logger.warning("SMTP error sending invitation email to %s: %s", to_email, exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("Failed to send invitation email to %s", to_email)
        raise self.retry(exc=exc)
