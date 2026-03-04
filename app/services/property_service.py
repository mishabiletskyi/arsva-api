from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.access_service import (
    can_access_property,
    can_manage_organization,
    can_manage_property,
    is_platform_owner,
)


def get_property_by_id(db: Session, property_id: int) -> Property | None:
    return (
        db.query(Property)
        .filter(Property.id == property_id)
        .first()
    )


def get_property_for_user(
    db: Session,
    user: AdminUser,
    property_id: int,
) -> Property | None:
    property_obj = get_property_by_id(db, property_id)
    if property_obj is None:
        return None

    if is_platform_owner(db, user):
        return property_obj

    if can_access_property(
        db=db,
        user=user,
        organization_id=property_obj.organization_id,
        property_id=property_obj.id,
    ):
        return property_obj

    return None


def get_properties(
    db: Session,
    current_user: AdminUser,
    skip: int = 0,
    limit: int = 50,
    organization_id: int | None = None,
) -> list[Property]:
    query = db.query(Property)

    if organization_id is not None:
        query = query.filter(Property.organization_id == organization_id)

    query = query.order_by(Property.name.asc())

    if is_platform_owner(db, current_user):
        return query.offset(skip).limit(limit).all()

    properties = query.all()
    scoped_properties = [
        item
        for item in properties
        if can_access_property(
            db=db,
            user=current_user,
            organization_id=item.organization_id,
            property_id=item.id,
        )
    ]

    return scoped_properties[skip : skip + limit]


def create_property(
    db: Session,
    payload: PropertyCreate,
    current_user: AdminUser,
) -> Property:
    if not can_manage_organization(
        db=db,
        user=current_user,
        organization_id=payload.organization_id,
    ):
        raise PermissionError("You do not have access to create properties in this organization")

    existing_property = (
        db.query(Property)
        .filter(
            Property.organization_id == payload.organization_id,
            Property.name == payload.name,
        )
        .first()
    )
    if existing_property is not None:
        raise ValueError("Property with this name already exists in this organization")

    property_obj = Property(**payload.model_dump())

    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)

    return property_obj


def update_property(
    db: Session,
    property_obj: Property,
    payload: PropertyUpdate,
    current_user: AdminUser,
) -> Property:
    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=property_obj.organization_id,
        property_id=property_obj.id,
    ):
        raise PermissionError("You do not have access to update this property")

    update_data = payload.model_dump(exclude_unset=True)

    new_name = update_data.get("name")
    if new_name:
        existing_property = (
            db.query(Property)
            .filter(
                Property.organization_id == property_obj.organization_id,
                Property.name == new_name,
                Property.id != property_obj.id,
            )
            .first()
        )
        if existing_property is not None:
            raise ValueError("Property with this name already exists in this organization")

    for field, value in update_data.items():
        setattr(property_obj, field, value)

    db.add(property_obj)
    db.commit()
    db.refresh(property_obj)

    return property_obj
