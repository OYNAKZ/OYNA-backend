from __future__ import annotations

import logging
from datetime import time

from sqlalchemy import select

from app.core.config import settings
from app.core.constants import SeatOperationalStatus, UserRole
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import Branch, Club, Seat, User, Zone
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

MOBILE_DEMO_EMAIL = "mobile@oyna.kz"
MOBILE_DEMO_PASSWORD = "mobile-password-123"
MOBILE_DEMO_CLUB_NAME = "OYNA Astana Demo"
MOBILE_DEMO_BRANCH_NAME = "Kabanbay Demo Hall"


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


def seed_mobile_demo_inventory() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == MOBILE_DEMO_EMAIL))
        if user is None:
            db.add(
                User(
                    email=MOBILE_DEMO_EMAIL,
                    password_hash=hash_password(MOBILE_DEMO_PASSWORD),
                    full_name="OYNA Mobile Demo",
                    role=UserRole.USER.value,
                    is_active=True,
                    is_email_verified=True,
                )
            )

        club = db.scalar(select(Club).where(Club.name == MOBILE_DEMO_CLUB_NAME))
        if club is None:
            club = Club(
                name=MOBILE_DEMO_CLUB_NAME,
                description="Demo gaming club for the mobile MVP in Astana.",
                is_active=True,
            )
            db.add(club)
            db.flush()

        branch = db.scalar(
            select(Branch).where(
                Branch.club_id == club.id,
                Branch.name == MOBILE_DEMO_BRANCH_NAME,
            )
        )
        if branch is None:
            branch = Branch(
                club_id=club.id,
                name=MOBILE_DEMO_BRANCH_NAME,
                address="проспект Кабанбай Батыра, 48",
                city="Астана",
                latitude=51.1282,
                longitude=71.4304,
                open_time=time(hour=10),
                close_time=time(hour=2),
                is_active=True,
            )
            db.add(branch)
            db.flush()

        zone = db.scalar(
            select(Zone).where(
                Zone.branch_id == branch.id,
                Zone.name == "Main Hall",
            )
        )
        if zone is None:
            zone = Zone(
                branch_id=branch.id,
                name="Main Hall",
                zone_type="gaming",
                description="Open gaming area with bookable demo seats.",
                is_active=True,
            )
            db.add(zone)
            db.flush()

        existing_codes = set(
            db.scalars(select(Seat.code).where(Seat.zone_id == zone.id))
        )
        for index in range(1, 13):
            code = f"A-{index:02d}"
            if code in existing_codes:
                continue
            db.add(
                Seat(
                    zone_id=zone.id,
                    code=code,
                    seat_type="standard" if index <= 8 else "vip",
                    is_active=True,
                    is_maintenance=False,
                    operational_status=SeatOperationalStatus.AVAILABLE.value,
                    x_position=float((index - 1) % 4),
                    y_position=float((index - 1) // 4),
                )
            )

        db.commit()
        logger.info("Seeded mobile demo inventory for %s", MOBILE_DEMO_CLUB_NAME)
