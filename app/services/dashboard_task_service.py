from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.models.dashboard_task import DashboardTask
from app.models.property import Property
from app.schemas.dashboard_task import DashboardTaskCreate, DashboardTaskUpdate
from app.services.access_service import can_access_property, can_manage_property, is_platform_owner

ALLOWED_DASHBOARD_STATUSES = {"pending", "in_progress", "done"}


def _validate_task_status(status_value: str) -> str:
    normalized = status_value.strip().lower()
    if normalized not in ALLOWED_DASHBOARD_STATUSES:
        raise ValueError("Unsupported dashboard task status")
    return normalized


def _get_scoped_task(db: Session, task_id: int, current_user: AdminUser) -> DashboardTask | None:
    task = (
        db.query(DashboardTask)
        .filter(DashboardTask.id == task_id)
        .first()
    )
    if task is None:
        return None

    if is_platform_owner(db, current_user):
        return task

    if not can_access_property(
        db=db,
        user=current_user,
        organization_id=task.organization_id,
        property_id=task.property_id,
    ):
        return None

    return task


def get_dashboard_tasks(
    db: Session,
    current_user: AdminUser,
    organization_id: int | None = None,
    property_id: int | None = None,
) -> list[DashboardTask]:
    query = db.query(DashboardTask)

    if organization_id is not None:
        query = query.filter(DashboardTask.organization_id == organization_id)
    if property_id is not None:
        query = query.filter(DashboardTask.property_id == property_id)

    tasks = query.order_by(DashboardTask.created_at.desc()).all()

    if is_platform_owner(db, current_user):
        return tasks

    return [
        task
        for task in tasks
        if can_access_property(
            db=db,
            user=current_user,
            organization_id=task.organization_id,
            property_id=task.property_id,
        )
    ]


def get_dashboard_task_by_id(
    db: Session,
    task_id: int,
    current_user: AdminUser,
) -> DashboardTask | None:
    return _get_scoped_task(db, task_id, current_user)


def create_dashboard_task(
    db: Session,
    payload: DashboardTaskCreate,
    current_user: AdminUser,
) -> DashboardTask:
    property_obj = (
        db.query(Property)
        .filter(Property.id == payload.property_id)
        .first()
    )
    if property_obj is None:
        raise ValueError("Property not found")

    if property_obj.organization_id != payload.organization_id:
        raise ValueError("organization_id does not match the selected property")

    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=payload.organization_id,
        property_id=payload.property_id,
    ):
        raise PermissionError("You do not have access to create tasks in this property")

    task = DashboardTask(
        organization_id=payload.organization_id,
        property_id=payload.property_id,
        title=payload.title.strip(),
        note=payload.note.strip() if payload.note else None,
        status=_validate_task_status(payload.status),
        created_by_admin_id=current_user.id,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def update_dashboard_task(
    db: Session,
    task: DashboardTask,
    payload: DashboardTaskUpdate,
    current_user: AdminUser,
) -> DashboardTask:
    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=task.organization_id,
        property_id=task.property_id,
    ):
        raise PermissionError("You do not have access to update this task")

    update_data = payload.model_dump(exclude_unset=True)

    if "title" in update_data and update_data["title"] is not None:
        update_data["title"] = update_data["title"].strip()
    if "note" in update_data and update_data["note"] is not None:
        update_data["note"] = update_data["note"].strip()
    if "status" in update_data and update_data["status"] is not None:
        update_data["status"] = _validate_task_status(update_data["status"])

    for field, value in update_data.items():
        setattr(task, field, value)

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


def delete_dashboard_task(
    db: Session,
    task: DashboardTask,
    current_user: AdminUser,
) -> None:
    if not can_manage_property(
        db=db,
        user=current_user,
        organization_id=task.organization_id,
        property_id=task.property_id,
    ):
        raise PermissionError("You do not have access to delete this task")

    db.delete(task)
    db.commit()
