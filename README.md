# Automated Rent Status Voice Assistant API

## Overview
This repository contains the backend API for the **Automated Rent Status Voice Assistant** MVP.

The service is built with:
- FastAPI
- PostgreSQL via SQLAlchemy
- Alembic for database migrations
- Azure Blob Storage for uploads and exports
- Vapi for voice calling
- Twilio for SMS and imported telephony scenarios

The backend is organized around a **multi-tenant** data model:
- an `Organization` represents a client company
- a `Property` represents a managed building or location
- `Tenant`, `CallLog`, `CsvImport`, `CallPolicy`, `DashboardTask`, and outbound jobs are all scoped to organization and property

This codebase is currently suitable for MVP demo delivery and controlled pilot work. Some settings remain intentionally demo-friendly and should be hardened before production rollout.

## Core Responsibilities
The API is responsible for:
- JWT authentication for admin users
- multi-tenant organization/property scope enforcement
- tenant CRUD and archive behavior
- CSV upload and tenant import
- outbound call job creation
- call policy storage and evaluation
- Vapi webhook handling and call log persistence
- optional SMS follow-up via Twilio
- CSV report generation

## Technology Stack
- Python 3.11 recommended for local development and Azure App Service
- FastAPI
- Uvicorn
- SQLAlchemy
- PostgreSQL (`psycopg`)
- Alembic
- Azure Blob Storage
- Vapi API
- Twilio API

## Repository Structure
Important paths:

- `app/main.py`  
  FastAPI bootstrap and middleware registration.

- `app/api/v1/endpoints/`  
  REST endpoint handlers.

- `app/services/`  
  Business logic, policy evaluation, import processing, telephony integration, reporting, and access control.

- `app/models/`  
  SQLAlchemy ORM models.

- `app/schemas/`  
  Pydantic request and response schemas.

- `alembic/versions/`  
  Database migration files.

- `.github/workflows/main_arsva-api.yml`  
  Azure App Service deployment workflow.

- `sample_data/`  
  Example CSV files for tenant import.

## Current Domain Model
Primary tables:
- `admin_users`
- `organizations`
- `properties`
- `admin_user_memberships`
- `property_user_access`
- `tenants`
- `call_logs`
- `csv_imports`
- `dashboard_tasks`
- `call_policies`
- `outbound_call_jobs`

Important role behavior:
- `AdminUser.is_superuser = true` is treated as platform owner
- membership roles currently supported:
  - `platform_owner`
  - `org_admin`
  - `property_manager`
  - `viewer`
- frontend-facing `role_ui` is simplified to:
  - `owner`
  - `manager`
  - `viewer`

## Main API Areas
The active API groups are registered in [`app/api/v1/router.py`](./app/api/v1/router.py):

- `Auth`
- `Admin Users`
- `Organizations`
- `Properties`
- `Tenants`
- `Tenant Eligibility`
- `CSV Imports`
- `Outbound Calls`
- `Call Logs`
- `Call Policy`
- `Dashboard Tasks`
- `Reports`
- `VAPI Webhooks`
- `Health`

## Quick Start
This section is intended for a new engineer who needs to run the backend locally with minimal guesswork.

### 1. Clone the repository
```powershell
git clone <REPOSITORY_URL>
cd arsva-api
```

### 2. Create and activate a virtual environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create `.env`
- create a `.env` file in the repository root
- use the template from the `Environment Configuration` section below
- fill in real values for PostgreSQL, Azure Blob, Vapi, Twilio, and JWT

### 5. Run database migrations
```powershell
alembic upgrade head
```

### 6. Start the API locally
```powershell
uvicorn app.main:app --reload
```

### 7. Open local endpoints
- Swagger UI: `http://127.0.0.1:8000/docs`
- Root endpoint: `http://127.0.0.1:8000/`
- Health endpoint: `http://127.0.0.1:8000/api/v1/health`

### 8. Perform a basic smoke test
1. call `POST /api/v1/auth/login`
2. call `GET /api/v1/auth/me`
3. upload a CSV through `POST /api/v1/csv-imports/upload`
4. confirm that scope-aware data is returned correctly

## Local Development Setup
### Prerequisites
The operator should have:
- Python 3.11 installed
- PostgreSQL available locally or remotely
- access to Azure Blob Storage
- access to Vapi
- access to Twilio if SMS or imported telephony is needed

### Local Installation
PowerShell example:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Environment Configuration
The working copy may already contain a `.env`, but the receiving team should create their own values and rotate all secrets before reuse.

Recommended local `.env` template:

```env
APP_NAME=Automated Rent Status Voice Assistant API
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

BACKEND_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=arsva_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

AZURE_BLOB_CONNECTION_STRING=REPLACE_ME
AZURE_BLOB_CONTAINER_UPLOADS=uploads
AZURE_BLOB_CONTAINER_EXPORTS=exports
AZURE_BLOB_CONTAINER_RECORDINGS=call-recordings

VAPI_PRIVATE_API_KEY=REPLACE_ME
VAPI_API_BASE_URL=https://api.vapi.ai
VAPI_DEFAULT_ASSISTANT_ID=REPLACE_ME
VAPI_PHONE_NUMBER_ID=REPLACE_ME
VAPI_WEBHOOK_SECRET=REPLACE_ME

TWILIO_ACCOUNT_SID=REPLACE_ME
TWILIO_AUTH_TOKEN=REPLACE_ME
TWILIO_FROM_PHONE_NUMBER=REPLACE_ME
TWILIO_API_BASE_URL=https://api.twilio.com/2010-04-01

SMS_AFTER_CALL_ENABLED=true
SMS_SEND_OUTCOMES=["paying_soon","need_assistance","needs_assistance"]
PAYMENT_PORTAL_URL=https://example.com/pay

JWT_SECRET_KEY=REPLACE_ME_WITH_LONG_RANDOM_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=180

MANAGER_SIGNUP_ENABLED=false
MANAGER_SIGNUP_CODE=REPLACE_ME_IF_SELF_SIGNUP_IS_USED
```

### Database Migration
After `.env` is configured:

```powershell
alembic upgrade head
```

This applies all migrations, including:
- initial schema
- multi-tenant foundation
- compliance fields
- dashboard tasks and outbound jobs
- call log SMS fields
- call policies
- CSV import soft delete fields

### Local Run Command
```powershell
uvicorn app.main:app --reload
```

Swagger UI:
- `http://127.0.0.1:8000/docs`

### Recommended Local Workflow
Typical local startup:

```powershell
.\.venv\Scripts\Activate.ps1
alembic upgrade head
uvicorn app.main:app --reload
```

If dependencies change:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Authentication and Access Model
### Login
- `POST /api/v1/auth/login`

### Current user
- `GET /api/v1/auth/me`

`/auth/me` returns:
- identity fields
- `role_ui`
- `current_organization`
- `available_properties`
- `current_property_id`
- memberships
- property accesses

### Self-signup
- `POST /api/v1/auth/register-manager`

Current behavior:
- self-signup is disabled by default
- if enabled, it requires a valid `signup_code`
- it accepts one of:
  - `organization_id`
  - `organization_slug`
  - `organization_name`

Important note:
- this flow is for manager onboarding, not owner bootstrap
- a platform owner account should be created and secured outside the public signup flow

## CSV Import Behavior
### Upload
- `POST /api/v1/csv-imports/upload`

The import:
- stores the uploaded CSV file in Azure Blob Storage
- creates a `csv_imports` history record
- creates `tenants` rows for valid lines
- stores row-level validation errors for failed lines

Accepted CSV format:
- header row is required
- supported delimiters: `,`, `;`, or tab
- minimum required columns:
  - `first_name`
  - `phone_number`

Recommended templates:
- [sample_data/tenants_import_template.csv](./sample_data/tenants_import_template.csv)
- [sample_data/tenants_import_5_demo.csv](./sample_data/tenants_import_5_demo.csv)

Supported columns:
- `external_id`
- `first_name`
- `last_name`
- `phone_number`
- `property_name`
- `timezone`
- `rent_due_date`
- `days_late`
- `consent_status`
- `consent_timestamp`
- `consent_source`
- `consent_document_version`
- `opt_out_flag`
- `opt_out_timestamp`
- `eviction_status`
- `is_suppressed`
- `notes`

### Delete
- `DELETE /api/v1/csv-imports/{id}`

Delete behavior is soft delete only:
- the `csv_imports` history record is marked deleted
- imported tenant data remains unchanged
- deleted records are excluded from:
  - `GET /api/v1/csv-imports`
  - `GET /api/v1/csv-imports/{id}`
  - CSV import report export

## Outbound Call Jobs
### Create
- `POST /api/v1/outbound-call-jobs`

The MVP frontend uses a simplified payload:

```json
{
  "organization_id": 1,
  "property_id": 1,
  "tenant_ids": [1, 2, 3],
  "trigger_mode": "manual",
  "dry_run": false,
  "max_tenants": 3
}
```

Notes:
- `organization_id` is effectively derived from scope and property
- `property_id` is the real scope selector for the selected tenants
- backend still runs policy and compliance validation internally

### Preferred response fields
The preferred MVP summary fields are:
- `requested_count`
- `started_count`
- `failed_count`
- `note`

Legacy fields such as `filters`, `policy_snapshot`, and `result_summary` may still appear for compatibility and audit needs.

## Call Policy
Call policy is managed separately from the tenant list UI.

Endpoints:
- `GET /api/v1/call-policy`
- `PUT /api/v1/call-policy`

Policy controls:
- minimum gap between calls
- max calls in 7 days
- max calls in 30 days
- allowed call window
- allowed `days_late` range
- active/inactive state

If no custom policy exists for a property, default policy values are used.

## Vapi Integration
### Purpose
Vapi is used for outbound voice calling and post-call webhook delivery.

### Required settings
- `VAPI_PRIVATE_API_KEY`
- `VAPI_DEFAULT_ASSISTANT_ID`
- `VAPI_PHONE_NUMBER_ID`
- `VAPI_WEBHOOK_SECRET`

### Webhook route
- `POST /api/v1/webhooks/vapi/calls`

### Important operational notes
- free Vapi phone numbers are suitable only for **US national use**
- international calling should use an imported provider number, typically Twilio
- the assistant configuration in Vapi should match the backend contract for tool calls and metadata payloads

## Twilio Integration
Twilio is currently used for SMS follow-up and may also be used for imported phone numbers when Vapi free numbers are not sufficient.

Required settings:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_PHONE_NUMBER`

Important note:
- SMS and voice are separate concerns in this project
- a Vapi voice number may be used for calling while Twilio remains responsible for SMS

## Azure Blob Storage
The backend uses Azure Blob Storage for:
- uploaded CSV source files
- exported report files
- call recording storage when configured

Required setting:
- `AZURE_BLOB_CONNECTION_STRING`

Default containers:
- `uploads`
- `exports`
- `call-recordings`

The receiving team should ensure these containers exist or are created as part of environment setup.

## Reports
Available CSV export endpoints:
- `/api/v1/reports/tenants.csv`
- `/api/v1/reports/call-logs.csv`
- `/api/v1/reports/csv-imports.csv`
- `/api/v1/reports/dashboard-tasks.csv`

Reports are scope-aware and may be filtered by organization, property, and date range.

## Azure App Service Deployment
### Runtime
Recommended:
- Python 3.11

### Deployment mechanism
This repository already includes a GitHub Actions workflow:
- [main_arsva-api.yml](./.github/workflows/main_arsva-api.yml)

### App Service requirements
The target Azure App Service should be configured with:
- correct Python runtime
- all required environment variables
- database connectivity to PostgreSQL
- outbound internet access to Vapi, Twilio, and Azure Blob

### Startup command
If a manual startup command is required:

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Deployment sequence
Recommended order:
1. update Azure environment variables
2. deploy code
3. run `alembic upgrade head`
4. restart the App Service
5. smoke test `/`, `/docs`, `/api/v1/health`, and `/api/v1/auth/login`

## CORS
At the time of writing, `app/main.py` is configured in a **demo-friendly** way and allows broad CORS access.

That is convenient for MVP demos but not appropriate for production.  
Before production launch, CORS should be restricted to the exact frontend domains in use.

## Security Notes
The receiving team should treat the current repository as sensitive because the working copy may contain real secrets in `.env`.

Before handoff or production rollout, the following should be completed:
- rotate PostgreSQL credentials
- rotate Azure Blob credentials
- rotate Vapi keys
- rotate Twilio credentials
- rotate the JWT secret
- rotate webhook and signup secrets
- confirm `.env` is excluded from Git history and deployment artifacts where appropriate

## Demo-Specific Notes
The current backend contains several demo-oriented decisions:
- broad CORS allowance
- manager self-signup can be enabled via invite code
- some compatibility fields remain in outbound job responses for older frontend builds
- free Vapi number support is limited to US-only calling

These decisions are acceptable for controlled demos but should be reviewed before a wider pilot or production launch.

## Troubleshooting
### Login works locally but not in frontend
Likely causes:
- frontend origin is not allowed by CORS
- Azure deployment is stale
- frontend points to the wrong API base URL

### Outbound job shows no started calls
Likely causes:
- tenant blocked by policy or compliance
- invalid `days_late`
- missing consent
- suppressed or opted-out tenant
- invalid `VAPI_PHONE_NUMBER_ID`
- free Vapi number being used for a non-US destination

### CSV import shows every value in one column
Likely causes:
- the CSV was saved with `;` as delimiter by Excel or local regional settings
- the file is not a real CSV export

The parser currently supports comma, semicolon, and tab delimiters. The safest option is to use one of the template files in `sample_data/`.

### CSV import record disappears after delete
This is expected. CSV delete is soft delete of the history record only.

### SMS is not sent
Likely causes:
- Twilio credentials are missing or invalid
- `TWILIO_FROM_PHONE_NUMBER` is not configured
- the outcome is not listed in `SMS_SEND_OUTCOMES`
- `PAYMENT_PORTAL_URL` is blank when a payment link is expected

### Migration fails on Azure
Likely causes:
- Azure environment variables do not match local expectations
- database firewall rules block the App Service
- the app was deployed before the latest migration files were included

## Handoff Checklist
Before transferring this repository, the following should be confirmed:
- all secrets have been rotated
- Azure App Service environment variables match the intended environment
- PostgreSQL migrations are up to date
- Vapi assistant and phone number IDs are current
- Twilio SMS credentials are valid if SMS is required
- Azure Blob containers are available
- the frontend API base URL points to the correct backend
- production CORS policy has been narrowed from demo mode

## Minimal Smoke Test
After setup, the receiving team should confirm:

1. `GET /api/v1/health` returns success
2. `POST /api/v1/auth/login` returns a JWT
3. `GET /api/v1/auth/me` returns scoped user data
4. `POST /api/v1/csv-imports/upload` creates a history item and tenant rows
5. `DELETE /api/v1/csv-imports/{id}` removes the import from history without deleting tenants
6. `POST /api/v1/outbound-call-jobs` creates a job and returns summary fields
7. `GET /api/v1/reports/*.csv` returns downloadable content

## Final Note
This backend is suitable for MVP demo delivery and controlled pilot usage.

Before production rollout, the receiving team should perform a dedicated hardening pass across:
- secrets management
- CORS restrictions
- role onboarding flow
- telephony provider strategy
- audit logging and compliance review
