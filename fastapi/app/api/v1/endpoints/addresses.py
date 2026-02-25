from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.address import Address
from app.models.user import User
from app.schemas.address import AddressCreate, AddressRead, AddressUpdate

router = APIRouter()


def _unset_defaults(db: Session, user_id: int) -> None:
    for address in db.scalars(select(Address).where(Address.user_id == user_id, Address.is_default.is_(True))).all():
        address.is_default = False


@router.get("/me", response_model=list[AddressRead])
def list_my_addresses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Address]:
    return list(db.scalars(select(Address).where(Address.user_id == current_user.id).order_by(Address.id.desc())).all())


@router.post("/me", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Address:
    if payload.is_default:
        _unset_defaults(db, current_user.id)

    address = Address(user_id=current_user.id, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.patch("/me/{address_id}", response_model=AddressRead)
def update_address(
    address_id: int,
    payload: AddressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Address:
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == current_user.id))
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    updates = payload.model_dump(exclude_unset=True)
    if updates.get("is_default") is True:
        _unset_defaults(db, current_user.id)

    for key, value in updates.items():
        setattr(address, key, value)

    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/me/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    address = db.scalar(select(Address).where(Address.id == address_id, Address.user_id == current_user.id))
    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")

    db.delete(address)
    db.commit()
