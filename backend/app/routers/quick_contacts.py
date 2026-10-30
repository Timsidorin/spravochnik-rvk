import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import require_admin
from ..database import get_db
from ..models import QuickContact
from ..schemas import QuickContactIn, QuickContactOut, QuickContactPatch

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quick-contacts", tags=["quick-contacts"])


async def _get_or_404(db: AsyncSession, contact_id: int) -> QuickContact:
    contact = await db.get(QuickContact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Номер не найден")
    return contact


@router.get("", response_model=list[QuickContactOut])
async def list_contacts(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(QuickContact).order_by(QuickContact.sort_order, QuickContact.id)
    )
    return rows.scalars().all()


@router.post("", response_model=QuickContactOut, status_code=201)
async def create_contact(
    payload: QuickContactIn,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    max_order = (await db.execute(select(func.max(QuickContact.sort_order)))).scalar() or 0
    contact = QuickContact(**payload.model_dump(), sort_order=max_order + 1)
    db.add(contact)
    await db.commit()
    log.info("Частый номер добавлен (%s): %s %s", user.get("sub"), contact.name, contact.phone)
    return contact


@router.put("/{contact_id}", response_model=QuickContactOut)
async def update_contact(
    contact_id: int,
    payload: QuickContactPatch,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    contact = await _get_or_404(db, contact_id)
    data = payload.model_dump(exclude_none=True)
    for field, value in data.items():
        setattr(contact, field, value)
    await db.commit()
    log.info("Частый номер %s изменён (%s): %s", contact_id, user.get("sub"), data)
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    contact = await _get_or_404(db, contact_id)
    await db.delete(contact)
    await db.commit()
    log.info("Частый номер %s удалён (%s)", contact_id, user.get("sub"))
    return Response(status_code=204)
