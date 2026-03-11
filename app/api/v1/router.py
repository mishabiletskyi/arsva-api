from fastapi import APIRouter

from app.api.v1.endpoints.admin_users import router as admin_users_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.call_logs import router as call_logs_router
from app.api.v1.endpoints.call_policy import router as call_policy_router
from app.api.v1.endpoints.csv_imports import router as csv_imports_router
from app.api.v1.endpoints.dashboard_tasks import router as dashboard_tasks_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.outbound_call_jobs import router as outbound_call_jobs_router
from app.api.v1.endpoints.properties import router as properties_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.tenant_eligibility import router as tenant_eligibility_router
from app.api.v1.endpoints.tenants import router as tenants_router
from app.api.v1.endpoints.vapi_webhooks import router as vapi_webhooks_router


api_router = APIRouter()

api_router.include_router(admin_users_router, tags=["Admin Users"])
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(auth_router, tags=["Auth"])
api_router.include_router(call_logs_router, tags=["Call Logs"])
api_router.include_router(call_policy_router, tags=["Call Policy"])
api_router.include_router(csv_imports_router, tags=["CSV Imports"])
api_router.include_router(dashboard_tasks_router, tags=["Dashboard Tasks"])
api_router.include_router(organizations_router, tags=["Organizations"])
api_router.include_router(outbound_call_jobs_router, tags=["Outbound Calls"])
api_router.include_router(properties_router, tags=["Properties"])
api_router.include_router(reports_router, tags=["Reports"])
api_router.include_router(tenant_eligibility_router, tags=["Tenant Eligibility"])
api_router.include_router(tenants_router, tags=["Tenants"])
api_router.include_router(vapi_webhooks_router, tags=["VAPI Webhooks"])
