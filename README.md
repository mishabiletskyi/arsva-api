# ARSVA API

## 2026-03-10 update

- Added scoped dynamic call policy configuration via:
  - `GET /api/v1/call-policy?organization_id=&property_id=`
  - `PUT /api/v1/call-policy`
- Eligibility and outbound dispatch now use policy values from DB per `(organization_id, property_id)`.
- Missing policy rows use fallback defaults (`72h`, `2/7d`, `4/30d`, `08:00-21:00`, `days_late 3-10`).
- Inactive policy (`is_active=false`) deterministically blocks outbound (`call_policy_inactive`).
- Outbound jobs now store `policy_snapshot` for auditability.
- JWT access token default TTL changed from `60` to `180` minutes (3 hours).
