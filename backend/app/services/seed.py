"""Seed initial data."""

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.database import async_session_maker
from app.models import MembershipType, Role


async def seed_membership_types() -> None:
    """Seed the 4 membership types."""
    types = [
        {
            "code": "NUMERARIO",
            "name": "Socio Numerario",
            "description": "Miembro regular mayor de 18 años",
            "can_vote": True,
            "can_be_elected": True,
            "discount_percentage": Decimal("0"),
            "is_free": False,
            "requires_study_certificate": False,
            "max_age": None,
            "allows_organization": False,
        },
        {
            "code": "HONORARIO",
            "name": "Socio Honorario",
            "description": "Reconocimiento honorífico, puede ser persona natural o jurídica",
            "can_vote": False,
            "can_be_elected": False,
            "discount_percentage": Decimal("100"),
            "is_free": True,
            "requires_study_certificate": False,
            "max_age": None,
            "allows_organization": True,
        },
        {
            "code": "FUNDADOR",
            "name": "Socio Fundador",
            "description": "Miembro fundador del club",
            "can_vote": True,
            "can_be_elected": True,
            "discount_percentage": Decimal("0"),
            "is_free": False,
            "requires_study_certificate": False,
            "max_age": None,
            "allows_organization": False,
        },
        {
            "code": "ESTUDIANTE",
            "name": "Socio Estudiante",
            "description": "Estudiante menor de 26 años con certificado de estudios",
            "can_vote": True,
            "can_be_elected": True,
            "discount_percentage": Decimal("50"),
            "is_free": False,
            "requires_study_certificate": True,
            "max_age": 26,
            "allows_organization": False,
        },
    ]

    async with async_session_maker() as session:
        for type_data in types:
            result = await session.execute(
                select(MembershipType).where(MembershipType.code == type_data["code"])
            )
            if not result.scalar_one_or_none():
                session.add(MembershipType(**type_data))
                print(f"  Created membership type: {type_data['code']}")
            else:
                print(f"  Membership type exists: {type_data['code']}")
        await session.commit()


async def seed_roles() -> None:
    """Seed default roles."""
    roles = [
        {"name": "MEMBER", "description": "Miembro regular del club"},
        {"name": "ADMIN", "description": "Administrador con acceso a gestión de socios"},
        {"name": "SUPER_ADMIN", "description": "Administrador con acceso total al sistema"},
    ]

    async with async_session_maker() as session:
        for role_data in roles:
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            if not result.scalar_one_or_none():
                session.add(Role(**role_data))
                print(f"  Created role: {role_data['name']}")
            else:
                print(f"  Role exists: {role_data['name']}")
        await session.commit()


async def seed_all() -> None:
    """Run all seed functions."""
    print("Seeding membership types...")
    await seed_membership_types()
    print("Seeding roles...")
    await seed_roles()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(seed_all())
