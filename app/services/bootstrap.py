from __future__ import annotations

import logging

from app.core.config import settings
from app.core.constants import UserRole
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


def seed_local_admin() -> None:
    email = (settings.dev_seed_admin_email or "").strip().lower()
    password = settings.dev_seed_admin_password or ""
    if not email or not password:
        return

    allowed_roles = {role.value for role in UserRole}
    role = settings.dev_seed_admin_role.strip().lower()
    if role not in allowed_roles:
        logger.warning("Skipping local admin seed because role %s is unsupported", settings.dev_seed_admin_role)
        return

    with SessionLocal() as db:
        repo = UserRepository(db)
        existing = repo.get_by_email(email)
        if existing is not None:
            logger.info("Local admin seed already exists for %s", email)
            return

        repo.create_user(
            email=email,
            password_hash=hash_password(password),
            full_name=settings.dev_seed_admin_full_name,
            role=role,
        )
        db.commit()
        logger.info("Seeded local admin account for %s with role %s", email, role)
