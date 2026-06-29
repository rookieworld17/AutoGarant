from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deal, User

OPPOSITE_ROLE = {"buyer": "seller", "seller": "buyer"}

ESCROW_STATUSES = ("escrow", "escrow_cancel")


class DealService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _generate_number(self) -> str:
        """Pick a 4-digit deal number that isn't taken yet."""
        while True:
            candidate = f"{secrets.randbelow(9000) + 1000}"
            result = await self._session.execute(
                select(Deal.id).where(Deal.number == candidate)
            )
            if result.scalar_one_or_none() is None:
                return candidate

    async def create(
        self,
        *,
        owner_id: int,
        owner_role: str,
        amount: Decimal,
        terms: str,
        expires_at: datetime | None = None,
    ) -> Deal:
        deal = Deal(
            number=await self._generate_number(),
            token=secrets.token_hex(16),
            owner_id=owner_id,
            owner_role=owner_role,
            amount=amount,
            terms=terms,
            status="active",
            expires_at=expires_at,
        )
        self._session.add(deal)
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def list_expired(self) -> list[Deal]:
        """Active deals whose TTL has passed — the work queue for the restart-safe
        expiry sweeper. Owner is eagerly loaded for rendering the notice."""
        result = await self._session.execute(
            select(Deal)
            .where(
                Deal.status == "active",
                Deal.expires_at.is_not(None),
                Deal.expires_at <= func.now(),
            )
            .options(selectinload(Deal.owner))
        )
        return list(result.scalars().all())

    async def get_by_token(self, token: str) -> Deal | None:
        result = await self._session.execute(
            select(Deal)
            .where(Deal.token == token)
            .options(selectinload(Deal.owner), selectinload(Deal.partner))
        )
        return result.scalar_one_or_none()

    async def count_for_user(self, user_id: int) -> int:
        """How many deals the user takes part in (owner or partner) — total for the
        'Мои сделки' pagination."""
        result = await self._session.execute(
            select(func.count())
            .select_from(Deal)
            .where(or_(Deal.owner_id == user_id, Deal.partner_id == user_id))
        )
        return int(result.scalar_one())

    async def list_for_user(
        self, user_id: int, *, offset: int, limit: int
    ) -> list[Deal]:
        """One page of the user's deals (owner or partner), newest first. Owner and
        partner are eagerly loaded so the list/detail cards can render both sides."""
        result = await self._session.execute(
            select(Deal)
            .where(or_(Deal.owner_id == user_id, Deal.partner_id == user_id))
            .order_by(Deal.created_at.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Deal.owner), selectinload(Deal.partner))
        )
        return list(result.scalars().all())

    async def get_with_users(self, deal_id: int) -> Deal | None:
        result = await self._session.execute(
            select(Deal)
            .where(Deal.id == deal_id)
            .options(selectinload(Deal.owner), selectinload(Deal.partner))
        )
        return result.scalar_one_or_none()

    async def accept(self, deal: Deal, partner_id: int) -> Deal:
        deal.partner_id = partner_id
        deal.status = "accepted"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def pay(self, deal: Deal, buyer: User) -> Deal:
        """Move an accepted deal into escrow: debit the buyer and hold the funds.

        The deal's expiry timer is dropped (``expires_at`` → None) — only unaccepted
        deals expire, and an escrowed deal must never be auto-closed."""
        buyer.deposit = buyer.deposit - deal.amount
        deal.status = "escrow"
        deal.expires_at = None
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def request_cancel(self, deal: Deal) -> Deal:
        """Mark a live deal as awaiting the other side's consent to cancel.

        Keeps the escrow marker (``escrow`` → ``escrow_cancel``) so a pending
        cancel knows the funds are held; an accepted deal goes to ``cancelling``."""
        deal.status = "escrow_cancel" if deal.status == "escrow" else "cancelling"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def set_cancel_request_message(self, deal: Deal, message_id: int) -> Deal:
        """Remember the partner's cancel-request message so it can be edited later."""
        deal.cancel_request_msg_id = message_id
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def revert_cancel(self, deal: Deal) -> Deal:
        """Undo a pending cancel request, restoring the pre-request state.

        ``escrow_cancel`` returns to ``escrow`` (funds stay held); ``cancelling``
        returns to ``accepted``. The remembered request message is forgotten."""
        deal.status = "escrow" if deal.status == "escrow_cancel" else "accepted"
        deal.cancel_request_msg_id = None
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def complete(self, deal: Deal, seller: User) -> Deal:
        """Release the escrowed funds to the seller and close the deal: credit the
        seller's balance and flip the status to 'completed'."""
        seller.deposit = seller.deposit + deal.amount
        deal.status = "completed"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def open_dispute(self, deal: Deal) -> Deal:
        """Open a dispute on an escrowed deal — the funds stay held while an admin
        decides the outcome. Cancellation and the receipt confirmation are blocked
        in this status (their handlers only run from 'escrow'/'accepted')."""
        deal.status = "dispute"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def resolve_dispute(self, deal: Deal, *, recipient: User, status: str) -> Deal:
        """Close a disputed deal by handing the held escrow funds to ``recipient``
        (the seller when the dispute is decided in the seller's favour, the buyer as
        a refund otherwise) and flipping the deal to its terminal ``status``
        ('completed' for a seller win, 'cancelled' for a buyer refund)."""
        recipient.deposit = recipient.deposit + deal.amount
        deal.status = status
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def expire(self, deal: Deal) -> Deal:
        deal.status = "expired"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal

    async def cancel(self, deal: Deal, *, refund_to: User | None = None) -> Deal:
        """Cancel a deal for good. If ``refund_to`` is given (the deal was in escrow),
        the held funds are returned to that buyer."""
        if refund_to is not None:
            refund_to.deposit = refund_to.deposit + deal.amount
        deal.status = "cancelled"
        await self._session.commit()
        await self._session.refresh(deal)
        return deal
