"""Skill2Job — skill-to-opportunity intelligence agent layer.

Built on the existing AI Hiring Copilot platform. Phase 1 establishes the
module foundation only:

* module health / capabilities endpoints
* candidate profile reuse (existing authentication + RBAC reused)

No fake intelligence is presented as implemented. Future phases add the
perception, profile, job, matching, gap, opportunity and training agents.
"""

from app.skill2job.router import router as skill2job_router

__all__ = ["skill2job_router"]