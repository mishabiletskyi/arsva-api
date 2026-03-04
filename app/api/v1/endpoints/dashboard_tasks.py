from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps.auth import get_current_user
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.dashboard_task import (
    DashboardTaskCreate,
    DashboardTaskResponse,
    DashboardTaskUpdate,
)
from app.services.dashboard_task_service import (
    create_dashboard_task,
    delete_dashboard_task,
    get_dashboard_task_by_id,
    get_dashboard_tasks,
    update_dashboard_task,
)

router = APIRouter(prefix="/dashboard-tasks")


@router.get("", response_model=list[DashboardTaskResponse], summary="Get dashboard tasks list")
def list_dashboard_tasks(
    organization_id: int | None = Query(default=None),
    property_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    return get_dashboard_tasks(
        db=db,
        current_user=current_user,
        organization_id=organization_id,
        property_id=property_id,
    )


@router.post("", response_model=DashboardTaskResponse, status_code=status.HTTP_201_CREATED, summary="Create dashboard task")
def create_dashboard_task_endpoint(
    payload: DashboardTaskCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    try:
        return create_dashboard_task(db=db, payload=payload, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.put("/{task_id}", response_model=DashboardTaskResponse, summary="Update dashboard task")
def update_dashboard_task_endpoint(
    task_id: int,
    payload: DashboardTaskUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    task = get_dashboard_task_by_id(db=db, task_id=task_id, current_user=current_user)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard task not found")

    try:
        return update_dashboard_task(db=db, task=task, payload=payload, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete dashboard task")
def delete_dashboard_task_endpoint(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    task = get_dashboard_task_by_id(db=db, task_id=task_id, current_user=current_user)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dashboard task not found")

    try:
        delete_dashboard_task(db=db, task=task, current_user=current_user)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
