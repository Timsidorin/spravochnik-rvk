import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, func
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


def _clean(name: str | None, phone: str | None) -> tuple[str | None, str | None]:
    # Код города не отрезаем: среди частых номеров бывают городские
    name = name.strip() if name is not None else None
    phone = phone.strip() if phone is not None else None
    return name, phone


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
    name, phone = _clean(payload.name, payload.phone)
    if not name or not phone:
        raise HTTPException(status_code=422, detail="Укажите название и номер")

    sort_order = payload.sort_order
    if not sort_order:
        max_order = (
            await db.execute(select(func.max(QuickContact.sort_order)))
        ).scalar() or 0
        sort_order = max_order + 1

    contact = QuickContact(name=name, phone=phone, sort_order=sort_order)
    db.add(contact)
    await db.commit()
    log.info("Частый номер добавлен (%s): %s %s", user.get("sub"), name, phone)
    return contact


@router.put("/{contact_id}", response_model=QuickContactOut)
async def update_contact(
    contact_id: int,
    payload: QuickContactPatch,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    contact = await _get_or_404(db, contact_id)
    data = payload.model_dump(exclude_unset=True)
    name, phone = _clean(data.get("name"), data.get("phone"))

    if "name" in data:
        if not name:
            raise HTTPException(status_code=422, detail="Название не может быть пустым")
        contact.name = name
    if "phone" in data:
        if not phone:
            raise HTTPException(status_code=422, detail="Номер не может быть пустым")
        contact.phone = phone
    if data.get("sort_order") is not None:
        contact.sort_order = data["sort_order"]

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
