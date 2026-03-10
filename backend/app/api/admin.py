"""Admin API endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.deps import AdminUser, DbSession
from app.models import Event, FeeRate, Membership, MembershipStatus, MembershipType, Payment, PaymentStatus, User
from app.schemas.admin import (
    EventCreate,
    EventUpdate,
    FeeRateCreate,
    MembershipApprove,
    MembershipListResponse,
    MembershipStatusUpdate,
    PaymentConfirm,
    PaymentCreate,
    PaymentResponse,
)
from app.schemas.event import EventResponse
from app.schemas.membership import FeeRateResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# === Membership Management ===

@router.get("/memberships", response_model=list[MembershipListResponse])
async def list_memberships(
    admin: AdminUser,
    db: DbSession,
    status_filter: MembershipStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List all memberships (admin only)."""
    query = (
        select(Membership)
        .options(
            selectinload(Membership.user),
            selectinload(Membership.membership_type),
        )
        .order_by(Membership.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter:
        query = query.where(Membership.status == status_filter)

    result = await db.execute(query)
    memberships = result.scalars().all()

    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "user_email": m.user.email,
            "user_full_name": m.user.full_name,
            "membership_type_code": m.membership_type.code,
            "membership_type_name": m.membership_type.name,
            "status": m.status,
            "start_date": m.start_date,
            "end_date": m.end_date,
            "created_at": m.created_at,
        }
        for m in memberships
    ]


@router.get("/memberships/pending/count")
async def count_pending_memberships(
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Count pending membership applications."""
    result = await db.execute(
        select(func.count(Membership.id))
        .where(Membership.status == MembershipStatus.PENDING)
    )
    count = result.scalar_one()
    return {"count": count}


@router.post("/memberships/{membership_id}/review")
async def review_membership(
    membership_id: str,
    review: MembershipApprove,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Approve or reject a membership application."""
    from uuid import UUID

    try:
        mid = UUID(membership_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid membership ID",
        )

    result = await db.execute(
        select(Membership)
        .where(Membership.id == mid)
        .options(selectinload(Membership.membership_type))
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    if membership.status != MembershipStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Membership is not pending (current: {membership.status.value})",
        )

    if review.action == "approve":
        membership.status = MembershipStatus.ACTIVE
        membership.approved_by = admin.id
        membership.approved_at = datetime.now()
    else:
        membership.status = MembershipStatus.CANCELLED

    if review.notes:
        existing_notes = membership.notes or ""
        membership.notes = f"{existing_notes}\n[Admin] {review.notes}".strip()

    await db.commit()

    return {
        "id": str(membership.id),
        "status": membership.status.value,
        "message": f"Membership {review.action}d successfully",
    }


@router.patch("/memberships/{membership_id}/status")
async def update_membership_status(
    membership_id: str,
    update: MembershipStatusUpdate,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Update membership status (suspend, expire, etc.)."""
    from uuid import UUID

    try:
        mid = UUID(membership_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid membership ID",
        )

    result = await db.execute(
        select(Membership).where(Membership.id == mid)
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    old_status = membership.status
    membership.status = update.status

    if update.notes:
        existing_notes = membership.notes or ""
        membership.notes = f"{existing_notes}\n[Admin] {old_status.value} -> {update.status.value}: {update.notes}".strip()

    await db.commit()

    return {
        "id": str(membership.id),
        "old_status": old_status.value,
        "new_status": membership.status.value,
    }


# === Payment Management ===

@router.get("/payments", response_model=list[PaymentResponse])
async def list_payments(
    admin: AdminUser,
    db: DbSession,
    status_filter: PaymentStatus | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    """List all payments (admin only)."""
    query = (
        select(Payment)
        .options(
            selectinload(Payment.membership).selectinload(Membership.user),
            selectinload(Payment.fee_rate),
        )
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if status_filter:
        query = query.where(Payment.status == status_filter)

    result = await db.execute(query)
    payments = result.scalars().all()

    return [
        {
            "id": p.id,
            "membership_id": p.membership_id,
            "user_email": p.membership.user.email,
            "user_full_name": p.membership.user.full_name,
            "fee_type": p.fee_rate.fee_type,
            "amount_clp": p.amount_clp,
            "payment_method": p.payment_method,
            "payment_date": p.payment_date,
            "period_month": p.period_month,
            "period_year": p.period_year,
            "status": p.status,
            "gateway_transaction_id": p.gateway_transaction_id,
            "transfer_proof_url": p.transfer_proof_url,
            "notes": p.notes,
            "confirmed_by": p.confirmed_by,
            "confirmed_at": p.confirmed_at,
            "created_at": p.created_at,
        }
        for p in payments
    ]


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreate,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Record a new payment (admin only)."""
    # Verify membership exists
    result = await db.execute(
        select(Membership)
        .where(Membership.id == payment_data.membership_id)
        .options(selectinload(Membership.user))
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Verify fee rate exists
    result = await db.execute(
        select(FeeRate).where(FeeRate.id == payment_data.fee_rate_id)
    )
    fee_rate = result.scalar_one_or_none()
    if not fee_rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fee rate not found",
        )

    payment = Payment(
        membership_id=payment_data.membership_id,
        fee_rate_id=payment_data.fee_rate_id,
        payment_method=payment_data.payment_method,
        amount_clp=payment_data.amount_clp,
        payment_date=payment_data.payment_date,
        period_month=payment_data.period_month,
        period_year=payment_data.period_year,
        status=PaymentStatus.PENDING,
        gateway_transaction_id=payment_data.gateway_transaction_id,
        transfer_proof_url=payment_data.transfer_proof_url,
        notes=payment_data.notes,
    )

    db.add(payment)
    await db.commit()
    await db.refresh(payment)

    return {
        "id": payment.id,
        "membership_id": payment.membership_id,
        "user_email": membership.user.email,
        "user_full_name": membership.user.full_name,
        "fee_type": fee_rate.fee_type,
        "amount_clp": payment.amount_clp,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date,
        "period_month": payment.period_month,
        "period_year": payment.period_year,
        "status": payment.status,
        "gateway_transaction_id": payment.gateway_transaction_id,
        "transfer_proof_url": payment.transfer_proof_url,
        "notes": payment.notes,
        "confirmed_by": payment.confirmed_by,
        "confirmed_at": payment.confirmed_at,
        "created_at": payment.created_at,
    }


@router.post("/payments/{payment_id}/confirm")
async def confirm_payment(
    payment_id: str,
    confirmation: PaymentConfirm,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Confirm or reject a pending payment."""
    from uuid import UUID

    try:
        pid = UUID(payment_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment ID",
        )

    result = await db.execute(
        select(Payment).where(Payment.id == pid)
    )
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment is not pending (current: {payment.status.value})",
        )

    if confirmation.action == "confirm":
        payment.status = PaymentStatus.CONFIRMED
        payment.confirmed_by = admin.id
        payment.confirmed_at = datetime.now()
    else:
        payment.status = PaymentStatus.REJECTED

    if confirmation.notes:
        existing_notes = payment.notes or ""
        payment.notes = f"{existing_notes}\n[Admin] {confirmation.notes}".strip()

    await db.commit()

    return {
        "id": str(payment.id),
        "status": payment.status.value,
        "message": f"Payment {confirmation.action}ed successfully",
    }


# === Event Management ===

@router.get("/events", response_model=list[EventResponse])
async def list_all_events(
    admin: AdminUser,
    db: DbSession,
    include_unpublished: bool = Query(True),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[Event]:
    """List all events including unpublished (admin only)."""
    query = (
        select(Event)
        .order_by(Event.event_date.desc())
        .limit(limit)
        .offset(offset)
    )

    if not include_unpublished:
        query = query.where(Event.is_published.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_data: EventCreate,
    admin: AdminUser,
    db: DbSession,
) -> Event:
    """Create a new event (admin only)."""
    event = Event(
        title=event_data.title,
        description=event_data.description,
        event_date=event_data.event_date,
        location=event_data.location,
        address=event_data.address,
        image_url=event_data.image_url,
        is_published=event_data.is_published,
        created_by=admin.id,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return event


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event_admin(
    event_id: str,
    admin: AdminUser,
    db: DbSession,
) -> Event:
    """Get any event including unpublished (admin only)."""
    from uuid import UUID

    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_data: EventUpdate,
    admin: AdminUser,
    db: DbSession,
) -> Event:
    """Update an event (admin only)."""
    from uuid import UUID

    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    update_data = event_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)

    return event


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: str,
    admin: AdminUser,
    db: DbSession,
) -> None:
    """Delete an event (admin only)."""
    from uuid import UUID

    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event ID",
        )

    result = await db.execute(
        select(Event).where(Event.id == eid)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    await db.delete(event)
    await db.commit()


# === Fee Rate Management ===

@router.post("/fee-rates", response_model=FeeRateResponse, status_code=status.HTTP_201_CREATED)
async def create_fee_rate(
    fee_data: FeeRateCreate,
    admin: AdminUser,
    db: DbSession,
) -> FeeRate:
    """Create a new fee rate (admin only)."""
    # Verify membership type exists
    result = await db.execute(
        select(MembershipType).where(MembershipType.id == fee_data.membership_type_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership type not found",
        )

    fee_rate = FeeRate(
        fee_type=fee_data.fee_type,
        membership_type_id=fee_data.membership_type_id,
        amount_utm=fee_data.amount_utm,
        utm_to_clp_rate=fee_data.utm_to_clp_rate,
        amount_clp=fee_data.amount_clp,
        effective_from=fee_data.effective_from,
        effective_until=fee_data.effective_until,
        reason=fee_data.reason,
        created_by=admin.id,
    )

    db.add(fee_rate)
    await db.commit()
    await db.refresh(fee_rate)

    return fee_rate


# === User Management ===

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    admin: AdminUser,
    db: DbSession,
    active_only: bool = Query(False),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
) -> list[User]:
    """List all users (admin only)."""
    query = (
        select(User)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if active_only:
        query = query.where(User.is_active.is_(True))

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    admin: AdminUser,
    db: DbSession,
) -> User:
    """Get a specific user (admin only)."""
    from uuid import UUID

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    result = await db.execute(
        select(User).where(User.id == uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    admin: AdminUser,
    db: DbSession,
) -> dict:
    """Activate or deactivate a user (admin only)."""
    from uuid import UUID

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID",
        )

    result = await db.execute(
        select(User).where(User.id == uid)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own status",
        )

    user.is_active = is_active
    await db.commit()

    return {
        "id": str(user.id),
        "is_active": user.is_active,
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
    }
