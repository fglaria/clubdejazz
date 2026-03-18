from uuid import UUID
from datetime import datetime, date, timezone
from typing import Annotated

from fastapi import HTTPException, status, Depends
from sqlalchemy import func, select, Result
from sqlalchemy.orm import selectinload

from app.core.deps import AsyncSession, DbSession
from app.models.membership import Membership, MembershipType, MembershipStatus
from app.models.user import User
from app.models.role import UserRole
from app.schemas.admin import MembershipApprove, MembershipStatusUpdate, MembershipAssign
from app.schemas.membership import MembershipApply
from app.services.user import UserServiceDependency


class MembershipService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self,
        status_filter: MembershipStatus | None,
        limit: int = 50,
        offset: int = 0
    ) -> list[Membership]:
        """List all memberships."""
        query = (
            select(Membership)
            .options(
                selectinload(Membership.user)
                    .selectinload(User.roles)
                    .selectinload(UserRole.role),
                selectinload(Membership.membership_type),
            )
            .order_by(Membership.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        if status_filter:
            query = query.where(Membership.status == status_filter)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_one(self, membership_id: str) -> Membership:
        """Get one membership by id."""
        try:
            mid: UUID = UUID(membership_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid membership ID",
            )

        query = (
            select(Membership)
            .where(Membership.id == mid)
            .options(selectinload(Membership.membership_type))
        )

        result: Result = await self.db.execute(query)
        membership: Membership | None = result.scalar_one_or_none()

        if not membership:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membership not found",
            )

        return membership

    async def review(self,
        membership_id: str,
        admin_id: UUID,
        review: MembershipApprove
    ) -> dict:
        """Approve or reject a membership application."""
        membership: Membership = await self.get_one(membership_id=membership_id)

        if membership.status != MembershipStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Membership is not pending (current: {membership.status.value})",
            )

        if review.action == "approve":
            membership.status = MembershipStatus.ACTIVE
            membership.approved_by = admin_id
            membership.approved_at = datetime.now(timezone.utc)
        else:
            membership.status = MembershipStatus.CANCELLED

        if review.notes:
            existing_notes = membership.notes or ""
            membership.notes = f"{existing_notes}\n[Admin] {review.notes}".strip()

        await self.db.commit()

        return {
            "id": str(membership.id),
            "status": membership.status.value,
            "message": f"Membership {review.action}d successfully",
        }

    async def update_status(self, membership_id: str, update: MembershipStatusUpdate) -> dict:
        membership: Membership = await self.get_one(membership_id=membership_id)

        old_status: MembershipStatus = membership.status
        membership.status = update.status

        if update.notes:
            existing_notes = membership.notes or ""
            membership.notes = f"{existing_notes}\n[Admin] {old_status} -> {update.status}: {update.notes}".strip()

        await self.db.commit()

        return {
            "id": str(membership.id),
            "old_status": old_status.value,
            "new_status": membership.status.value,
        }

    async def of_user(self, user_id: str) -> list[Membership]:
        """Get user's memberships."""
        query = (
            select(Membership)
            .where(Membership.user_id == user_id)
            .options(selectinload(Membership.membership_type))
            .order_by(Membership.created_at.desc())
        )

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def apply(self, user_id: str, application: MembershipApply) -> Membership:
        """Apply for a membership."""
        # Check if user already has an active or pending membership
        valid_statuses: list[MembershipStatus] = [MembershipStatus.ACTIVE, MembershipStatus.PENDING]
        query = (
            select(Membership)
            .where(Membership.user_id == user_id)
            .where(Membership.status.in_(valid_statuses))
        )

        result: Result = await self.db.execute(query)
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active or pending membership",
            )

        # Get membership type
        membership_type_code: str = application.membership_type_code.upper()
        membership_type: MembershipType = await self.get_type_by_code(
            membership_type_code=membership_type_code
        )

        # Create membership application
        membership = Membership(
            user_id=user_id,
            membership_type_id=membership_type.id,
            status=MembershipStatus.PENDING,
            start_date=date.today(),
            sponsored_by_1=application.sponsored_by_1,
            sponsored_by_2=application.sponsored_by_2,
            notes=application.notes,
        )
        self.db.add(membership)
        await self.db.commit()

        # Reload with relationships
        query = (
            select(Membership)
            .where(Membership.id == membership.id)
            .options(selectinload(Membership.membership_type))
        )

        result = await self.db.execute(query)
        return result.scalar_one()

    async def assign_to_user(self,
        body: MembershipAssign,
        admin_id: UUID,
        user_service: UserServiceDependency
    ) -> Membership:
        """Assign an active membership to an existing user (admin only)."""
        # Fetch user to check if exists
        user: User = user_service.get_one(user_id=body.user_id)

        # Check no ACTIVE or PENDING membership
        valid_statuses: list[MembershipStatus] = [MembershipStatus.ACTIVE, MembershipStatus.PENDING]
        query = (
            select(Membership)
            .where(Membership.user_id == body.user_id)
            .where(Membership.status.in_(valid_statuses))
        )

        result: Result = await self.db.execute(query)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario ya tiene una membresía activa o pendiente",
            )

        # Resolve membership type
        membership_type_code: str = body.membership_type_code.upper()
        membership_type: MembershipType = await self.get_type_by_code(
            membership_type_code=membership_type_code
        )

        # Create active membership
        membership: Membership = Membership(
            user_id=user.id,
            membership_type_id=membership_type.id,
            status=MembershipStatus.ACTIVE,
            start_date=date.today(),
            approved_by=admin_id,
            approved_at=datetime.now(),
        )
        self.db.add(membership)
        await self.db.commit()

        # Re-query with relationships loaded
        query = (
            select(Membership)
            .where(Membership.id == membership.id)
            .options(
                selectinload(Membership.user),
                selectinload(Membership.membership_type),
            )
        )

        result = await self.db.execute(query)
        return result.scalar_one()

    async def count_type(self, membership_status: MembershipStatus) -> dict:
        """Count membership applications of specified status."""
        result = await self.db.execute(
            select(func.count(Membership.id))
            .where(Membership.status == membership_status)
        )
        count: int = result.scalar_one()
        return {"status": membership_status, "count": count}

    async def get_types(self) -> list[MembershipType]:
        """List all MembershipTypes"""
        query = select(MembershipType)

        result: Result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_type_by_code(self, membership_type_code: str) -> MembershipType:
        """Get one MembershipType by code"""
        query = (
            select(MembershipType)
            .where(MembershipType.code == membership_type_code)
        )

        result: Result = await self.db.execute(query)
        membership_type: MembershipType | None = result.scalar_one_or_none()
        if not membership_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Membership type '{membership_type_code}' not found",
            )

        return membership_type


def get_membership_service(db: DbSession) -> MembershipService:
    """Get Membership Service"""
    return MembershipService(db=db)


MembershipServiceDependency = Annotated[MembershipService, Depends(get_membership_service)]
