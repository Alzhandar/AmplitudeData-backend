# Employee / EmployeeOrganization / Division / Position / Organization API Documentation

## 1. Scope and Sources

This document describes how employee-related domain entities and APIs work in the current codebase:

- Models: Employee, Position, Division, EmployeeOrganization, Organization
- Directly related models: EmployeeBlacklistExemption, EmployeeIdentification, EmployeeDiscountPolicy, EmployeeDiscountUsage, Park, CashRegister
- API endpoints under `/api/v1/` for these entities and related employee flows
- Validation and side effects (guest blacklist and terminal sync)

All statements below are based on the current source code.

---

## 2. Global API Contract

### 2.1 Base URL

All registered DRF router endpoints are under:

- `/api/v1/`

### 2.2 Authentication

Default DRF authentication classes:

- Basic auth
- Bearer token auth (`Authorization: Bearer <token>`)

Implementation:

- `big_data_app/authentications.py` (`BearerAuthentication`)

### 2.3 Permissions

Default DRF permission class:

- `BigDataDjangoModelPermissions`

Behavior:

- GET/HEAD/OPTIONS require Django `view` permission on model
- POST/PATCH/DELETE use standard Django model permissions from `DjangoModelPermissions`

Override exceptions in related APIs:

- `EmployeeIdentificationViewSet` uses `AllowAny`
- Employee discount endpoints use `IsAuthenticated`

### 2.4 Filtering, search, ordering, pagination

Default DRF filter backends:

- DjangoFilterBackend
- SearchFilter
- OrderingFilter

Default pagination:

- PageNumberPagination
- Page size: 50

Some employee-related viewsets override pagination to `None`.

---

## 3. Domain Models

## 3.1 BaseModelClass

All core entities below inherit:

- `time_create` (auto_now_add)
- `time_update` (auto_now)

## 3.2 Position

Model: `Position` (declared in `big_data_app/models/employee.py`)

Fields:

- `name`: Char(100), not unique
- `guid_1c`: Char(50), unique, nullable
- inherited: `time_create`, `time_update`

Used by:

- `Employee.position`
- `EmployeeBlacklistExemption.position`

## 3.3 Division

Model file: `big_data_app/models/division.py`

Fields:

- `name`: Char(100), not unique
- `guid_1c`: Char(50), unique, nullable
- inherited: `time_create`, `time_update`

Used by:

- `Employee.division`

## 3.4 EmployeeOrganization

Model file: `big_data_app/models/employee_organization.py`

Fields:

- `name`: Char(100), not unique
- `guid_1c`: Char(50), unique, nullable
- `bin`: Char(12), nullable
- inherited: `time_create`, `time_update`

Used by:

- `Employee.employee_organization`
- `EmployeeBlacklistExemption.organization`

## 3.5 Employee

Model: `Employee` (declared in `big_data_app/models/employee.py`)

Fields:

- `iin`: Char(12), unique, required
- `full_name`: Char(255), required
- `photo`: Text, nullable
- `active`: Boolean, default True
- `hired_date`: DateTime, nullable
- `fired_date`: DateTime, nullable
- `employee_organization`: FK -> EmployeeOrganization, nullable, `on_delete=CASCADE`
- `position`: FK -> Position, nullable, `on_delete=CASCADE`
- `phone`: Char(20), nullable
- `email`: Email, nullable
- `experience`: Integer, nullable
- `division`: FK -> Division, nullable, `on_delete=CASCADE`
- `park`: FK -> Park, nullable, `on_delete=CASCADE`
- inherited: `time_create`, `time_update`

## 3.6 Organization (separate business entity)

Model file: `big_data_app/models/organization.py`

Fields:

- `name`: Char(255)
- `full_name`: Char(255)
- `guid_1c`: Char(36), unique, nullable
- `kbe`: SmallInteger, default 0
- `bin`: Char(12)
- `okpo`: Char(10)
- inherited: `time_create`, `time_update`

Important:

- `Employee` does NOT reference `Organization`
- Employee APIs use `EmployeeOrganization` (separate model)

Used by:

- `CashRegister.organization`

## 3.7 EmployeeBlacklistExemption (related behavior model)

Model file: `big_data_app/models/employee_blacklist_exemption.py`

Purpose:

- Defines exclusion rules from guest auto-blocking for employees.

Fields:

- `organization`: FK -> EmployeeOrganization, nullable
- `position`: FK -> Position, nullable
- `is_active`: bool
- `description`: text nullable
- inherited: `time_create`, `time_update`

Rules:

- `unique_together = (organization, position)`
- validation requires at least one of `organization` or `position`

## 3.8 EmployeeIdentification (related event model)

Model file: `big_data_app/models/employee_identification.py`

Fields:

- `auth_time`: DateTime
- `employee`: FK -> Employee (`SET_NULL`)
- `park`: FK -> Park (`SET_NULL`)
- `employeeNo`: Char(64)
- inherited: `time_create`, `time_update`

## 3.9 EmployeeDiscount models (related business logic)

Model file: `big_data_app/models/employee_discount.py`

Entities:

- `EmployeeDiscountPolicy`
- `EmployeeDiscountUsage`

`EmployeeDiscountUsage` links employee + order + policy.

---

## 4. Relationship Map

Core employee graph:

- Employee -> EmployeeOrganization
- Employee -> Position
- Employee -> Division
- Employee -> Park

Related graph:

- EmployeeBlacklistExemption -> EmployeeOrganization / Position
- EmployeeIdentification -> Employee / Park
- EmployeeDiscountUsage -> Employee / Order / EmployeeDiscountPolicy
- CashRegister -> Organization

---

## 5. API Endpoints: Core Domain

## 5.1 Employees V2

Router:

- `employees` -> `EmployeeV2ViewSet`

Base path:

- `/api/v1/employees/`

Lookup:

- by `iin` (not by numeric id)
- detail path format: `/api/v1/employees/{iin}/`

Methods:

- GET list
- GET retrieve
- POST create
- PUT update
- PATCH partial update
- DELETE soft delete

Serializer mapping:

- list/retrieve -> `EmployeeRetrieveSerializer`
- create -> `EmployeeCreateSerializer`
- update/partial_update -> `EmployeeUpdateSerializer`

Create/update input field contract:

- `organization_guid` expects `EmployeeOrganization.guid_1c`
- `position` expects `Position.guid_1c`
- `division` expects `Division.guid_1c`
- `park` expects Park id

Response model for retrieve/list item:

- `position` returns position GUID (`position.guid_1c`)
- `division` returns division GUID (`division.guid_1c`)
- `organization_guid` returns employee organization GUID
- `park` returns park id

Employee filters (`EmployeeFilter`):

- `active` (exact)
- `id` (exact)
- `position` (`position__name icontains`)
- `phone` (`icontains`)
- `name` (`full_name icontains`)
- `employee_organization` (`employee_organization__id exact`)
- `division` (`division__name icontains`)
- `park` (`park__id exact`)
- `experience` (exact)

### 5.1.1 Side effects on create/update

When employee is created/updated:

1. Guest auto-block check by phone may run.
2. Terminal sync may run (create).
3. Face upload to terminal may run when photo changed (update/patch).

Implementation details:

- Serializer create calls `block_guest_by_phone_if_employee(...)`
- View create also calls `block_guest_if_employee(...)` and then terminal sync
- View update/patch calls `block_guest_if_employee(...)`
- View update/patch uploads face when `photo` changed

### 5.1.2 DELETE behavior

Delete is soft-delete style in this viewset:

- sets `active=False`
- sets `fired_date=now`
- does not physically remove employee row

---

## 5.2 Positions

Router:

- `position` -> `PositionViewSet`

Base path:

- `/api/v1/position/`

Lookup:

- by `guid_1c`

Allowed methods:

- GET, POST, PATCH, DELETE
- PUT is not allowed by this viewset

Filters/search/order:

- filter: `name`, `id`, `guid_1c`
- search: `id`, `name`, `guid_1c`
- ordering: `name`, `id`

Serializers:

- create -> `PositionCreateSerializer`
- list/retrieve -> `PositionRetrieveSerializer`
- patch -> `PositionUpdateSerializer`

---

## 5.3 Divisions

Router:

- `division` -> `DivisionViewSet`

Base path:

- `/api/v1/division/`

Lookup:

- by `guid_1c`

Allowed methods:

- GET, POST, PATCH, DELETE
- PUT is not allowed by this viewset

Filters/search/order:

- filter: `name`, `id`
- search: `id`, `name`
- ordering: `name`, `id`

Serializers:

- create -> `DivisionCreateSerializer`
- list/retrieve -> `DivisionRetrieveSerializer`
- patch -> `DivisionUpdateSerializer`

---

## 5.4 Employee Organizations

Router:

- `employee-organization` -> `EmployeeOrganizationViewSet`

Base path:

- `/api/v1/employee-organization/`

Lookup:

- by `guid_1c`

Allowed methods:

- GET, POST, PATCH, DELETE
- PUT is not allowed by this viewset

Filters/search/order:

- filter: `name`, `id`, `bin`
- search: `id`, `name`, `bin`
- ordering: `name`, `id`

Serializers:

- create -> `EmployeeOrganizationCreateSerializer`
- list/retrieve -> `EmployeeOrganizationRetrieveSerializer`
- patch -> `EmployeeOrganizationUpdateSerializer`

Response envelope style:

- custom response object (`success`, `id`, `data`, `error`, etc.)

---

## 5.5 Organizations (business organizations)

Router:

- `organization` -> `OrganizationViewSet`

Base path:

- `/api/v1/organization/`

Lookup:

- default DRF pk (id)

Methods:

- full ModelViewSet CRUD (GET/POST/PUT/PATCH/DELETE)

Serializer:

- `OrganizationSerializer` with `fields = "__all__"`

Filters/order:

- filter: `name`, `bin`, `guid_1c`
- ordering: `id`, `name`, `bin`
- default ordering: `id`

Important:

- This model is separate from `EmployeeOrganization`.

---

## 6. Related Employee APIs

## 6.1 Employee Time Tracker fetch

Router:

- `employee-time-tracker` -> `EmployeeViewSet`

Path:

- `/api/v1/employee-time-tracker/`

Behavior:

- GET list calls TimeTracker client and returns transformed external employee data.
- This endpoint does not create local employees.

## 6.2 Employee Identification

Routers:

- `employee-identification` -> `EmployeeIdentificationViewSet`
- `employee-identification-list` -> `EmployeeIdentificationList`

Paths:

- `/api/v1/employee-identification/`
- `/api/v1/employee-identification/missing/`
- `/api/v1/employee-identification/organization-period/`
- `/api/v1/employee-identification-list/`

Permissions:

- `employee-identification` uses `AllowAny`

Notable behavior:

- Ingests terminal/webhook events in multiple payload formats.
- Creates EmployeeIdentification records when employee can be resolved.
- Includes analytical actions:
  - `missing`: active employees without morning identification
  - `organization-period`: first/last identification per employee per day in period

## 6.3 Employee Discount

Registered routers:

- `employee-discount/check` -> `EmployeeDiscountCheckViewSet`
- `employee-discount-usage` -> `EmployeeDiscountUsageViewSet`

Paths:

- `/api/v1/employee-discount/check/`
- `/api/v1/employee-discount-usage/`
- `/api/v1/employee-discount-usage/by-employee/{employee_id}/`
- `/api/v1/employee-discount-usage/by_month/?month=YYYY-MM`

Permissions:

- `IsAuthenticated`

Important router note:

- `EmployeeDiscountPolicyViewSet` exists in code but is not registered in `big_data_project/urls.py`, so no public router endpoint currently exposed for policy CRUD.

---

## 7. Validation and Data Rules

## 7.1 Employee create/update validators

- IIN must be unique on create.
- `position`, `organization_guid`, `division` are validated by GUID existence.
- `park` is validated by id existence.
- `fired_date` cannot be earlier than `hired_date` (create serializer).
- phone is normalized to digit format, preferring `7XXXXXXXXXX`.
- photo can be:
  - URL
  - preformatted S3 employee path
  - base64 image (auto-uploaded to S3)

## 7.2 Guest auto-blocking rule (employee phone overlap)

On employee create/update, service checks whether a guest with same phone exists.
If employee is active and not matched by exemption rules:

- guest is marked blocked (`black_list = BLOCKED`)
- block time is set if empty

Exemption model:

- `EmployeeBlacklistExemption`
- active rules by organization and/or position

---

## 8. Endpoint Catalog (Quick Reference)

Core:

- `/api/v1/employees/`
- `/api/v1/position/`
- `/api/v1/division/`
- `/api/v1/employee-organization/`
- `/api/v1/organization/`

Related:

- `/api/v1/employee-time-tracker/`
- `/api/v1/employee-identification/`
- `/api/v1/employee-identification/missing/`
- `/api/v1/employee-identification/organization-period/`
- `/api/v1/employee-identification-list/`
- `/api/v1/employee-discount/check/`
- `/api/v1/employee-discount-usage/`

---

## 9. Integration Notes for a New Project

1. Do not mix `Organization` and `EmployeeOrganization` in API contracts.
2. For employee write APIs, pass GUIDs for relation fields:
   - `organization_guid`, `position`, `division`
3. Employee detail lookup is by IIN, not by id.
4. If you replicate behavior, account for side effects:
   - guest auto-block
   - terminal sync
   - optional face upload
5. If you need discount policy CRUD API, router registration for `EmployeeDiscountPolicyViewSet` must be added explicitly.

---

## 10. Known Implementation Nuances (As-Is)

These are not assumptions; these are current-code nuances to keep in mind:

- In employee identification filters/actions, some organization filters use `organization` field name while employee model uses `employee_organization`. If you replicate queries in another project, align field names carefully.
- Position/Division/EmployeeOrganization viewsets only support PATCH for updates (PUT disabled by `http_method_names`).
- Employee create path may call guest-block logic from both serializer and view layer.

---

## 11. API JSON Contracts (Body, Filters, Return)

This section is the practical contract for integration: what can be sent, available filters, and real response shapes.

## 11.1 Employees (`/api/v1/employees/`)

### 11.1.1 Create employee (POST)

Request body (JSON):

```json
{
  "iin": "123456789012",
  "full_name": "John Doe",
  "photo": "https://example.com/photo.jpg",
  "active": true,
  "hired_date": "2026-04-21T09:00:00Z",
  "fired_date": null,
  "organization_guid": "ORG-GUID-001",
  "position": "POS-GUID-001",
  "phone": "87071362645",
  "email": "john.doe@example.com",
  "experience": 12,
  "division": "DIV-GUID-001",
  "park": 2
}
```

Notes:

- `organization_guid`, `position`, `division` are GUIDs.
- `park` is numeric park id.
- `photo` may be URL/base64/S3 path.

Success response (201):

```json
{
  "id": 101,
  "message": "Сотрудник успешно создан",
  "data": {
    "iin": "123456789012",
    "full_name": "John Doe",
    "photo": "https://example.com/photo.jpg",
    "active": true,
    "hired_date": "2026-04-21T09:00:00Z",
    "fired_date": null,
    "organization_guid": "ORG-GUID-001",
    "position": "POS-GUID-001",
    "phone": "77071362645",
    "email": "john.doe@example.com",
    "experience": 12,
    "division": "DIV-GUID-001",
    "park": 2
  },
  "error": []
}
```

Validation error example (400):

```json
{
  "iin": [
    "Сотрудник с ИИН 123456789012 уже существует"
  ]
}
```

### 11.1.2 Employees list (GET)

Supported filters (query params):

- `active` (bool)
- `id` (int)
- `position` (substring of position name)
- `phone` (substring)
- `name` (substring of full name)
- `employee_organization` (organization id)
- `division` (substring of division name)
- `park` (park id)
- `experience` (int)

Example query:

`/api/v1/employees/?active=true&park=2&division=sales&name=john`

Paginated response shape (default):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": {
    "data": [
      {
        "id": 101,
        "iin": "123456789012",
        "full_name": "John Doe",
        "photo": "https://example.com/photo.jpg",
        "active": true,
        "hired_date": "2026-04-21T09:00:00Z",
        "fired_date": null,
        "phone": "77071362645",
        "email": "john.doe@example.com",
        "organization_guid": "ORG-GUID-001",
        "position": "POS-GUID-001",
        "experience": 12,
        "division": "DIV-GUID-001",
        "park": 2
      }
    ],
    "error": []
  }
}
```

Non-paginated fallback response shape:

```json
{
  "success": true,
  "data": [],
  "error": []
}
```

### 11.1.3 Employee retrieve (GET by IIN)

Path:

- `/api/v1/employees/{iin}/`

Success response (200):

```json
{
  "success": true,
  "id": 101,
  "data": {
    "id": 101,
    "iin": "123456789012",
    "full_name": "John Doe",
    "photo": "https://example.com/photo.jpg",
    "active": true,
    "hired_date": "2026-04-21T09:00:00Z",
    "fired_date": null,
    "phone": "77071362645",
    "email": "john.doe@example.com",
    "organization_guid": "ORG-GUID-001",
    "position": "POS-GUID-001",
    "experience": 12,
    "division": "DIV-GUID-001",
    "park": 2
  },
  "error": []
}
```

Not found example (404):

```json
{
  "detail": "Сотрудник с ИИН '123456789012' не найден"
}
```

### 11.1.4 Employee update (PUT/PATCH by IIN)

Path:

- `/api/v1/employees/{iin}/`

PATCH body example:

```json
{
  "full_name": "John Doe Updated",
  "phone": "+7 (707) 136-26-45",
  "organization_guid": "ORG-GUID-002",
  "position": "POS-GUID-002",
  "division": "DIV-GUID-002",
  "park": 4
}
```

PATCH response (200):

```json
{
  "success": true,
  "id": 101,
  "data": {
    "iin": "123456789012",
    "full_name": "John Doe Updated",
    "photo": "https://example.com/photo.jpg",
    "active": true,
    "hired_date": "2026-04-21T09:00:00Z",
    "fired_date": null,
    "organization_guid": "ORG-GUID-002",
    "position": "POS-GUID-002",
    "phone": "77071362645",
    "email": "john.doe@example.com",
    "experience": 12,
    "division": "DIV-GUID-002",
    "park": 4
  },
  "error": []
}
```

PUT response (200) has same shape, with additional message:

```json
{
  "success": true,
  "id": 101,
  "message": "Сотрудник успешно обновлен",
  "data": {},
  "error": []
}
```

### 11.1.5 Employee delete (DELETE by IIN)

Path:

- `/api/v1/employees/{iin}/`

Actual behavior:

- Sets `active=false` and `fired_date=now`
- Returns HTTP 204 No Content (empty body)

---

## 11.2 Position (`/api/v1/position/`)

Lookup field: `guid_1c`

### 11.2.1 Create (POST)

Body:

```json
{
  "name": "Administrator",
  "guid_1c": "POS-GUID-001"
}
```

Response (201):

```json
{
  "id": 10,
  "message": "Должность успешно создана",
  "data": {
    "name": "Administrator",
    "guid_1c": "POS-GUID-001"
  },
  "error": []
}
```

### 11.2.2 List (GET)

Filters:

- `name`
- `id`
- `guid_1c`

Search:

- `search` over `id,name,guid_1c`

Ordering:

- `ordering=name` or `ordering=id`

Response (200 non-paginated):

```json
{
  "success": true,
  "data": [
    {
      "name": "Administrator",
      "guid_1c": "POS-GUID-001"
    }
  ],
  "error": []
}
```

Paginated shape uses `count/next/previous/results` wrapper with `results.data`.

### 11.2.3 Retrieve (GET by guid_1c)

Path:

- `/api/v1/position/{guid_1c}/`

Response (200):

```json
{
  "success": true,
  "id": 10,
  "data": {
    "name": "Administrator",
    "guid_1c": "POS-GUID-001"
  },
  "error": []
}
```

### 11.2.4 Partial update (PATCH by guid_1c)

Body:

```json
{
  "name": "Senior Administrator"
}
```

Response (200):

```json
{
  "success": true,
  "id": 10,
  "data": {
    "name": "Senior Administrator",
    "guid_1c": "POS-GUID-001"
  },
  "error": []
}
```

### 11.2.5 Delete (DELETE by guid_1c)

Actual runtime response:

- HTTP 204 No Content (empty body)

---

## 11.3 Division (`/api/v1/division/`)

Lookup field: `guid_1c`

### 11.3.1 Create (POST)

Body:

```json
{
  "name": "Sales",
  "guid_1c": "DIV-GUID-001"
}
```

Response (201):

```json
{
  "id": 20,
  "message": "Подразделение успешно создано",
  "data": {
    "name": "Sales",
    "guid_1c": "DIV-GUID-001"
  },
  "error": []
}
```

### 11.3.2 List / filters (GET)

Filters:

- `name`
- `id`

Search:

- `search` over `id,name`

Ordering:

- `ordering=name` or `ordering=id`

Response shape is same pattern as Position.

### 11.3.3 Retrieve / PATCH / DELETE

Paths:

- `/api/v1/division/{guid_1c}/`

PATCH body:

```json
{
  "name": "Sales East"
}
```

PATCH response (200):

```json
{
  "success": true,
  "id": 20,
  "data": {
    "name": "Sales East",
    "guid_1c": "DIV-GUID-001"
  },
  "error": []
}
```

DELETE response:

- HTTP 204 No Content (empty body)

---

## 11.4 EmployeeOrganization (`/api/v1/employee-organization/`)

Lookup field: `guid_1c`

### 11.4.1 Create (POST)

Body:

```json
{
  "name": "Head Office",
  "guid_1c": "ORG-GUID-001",
  "bin": "123456789012"
}
```

Response (201):

```json
{
  "id": 30,
  "message": "Организация сотрудника успешно создана",
  "data": {
    "name": "Head Office",
    "guid_1c": "ORG-GUID-001",
    "bin": "123456789012"
  },
  "error": []
}
```

### 11.4.2 List (GET)

Filters:

- `name`
- `id`
- `bin`

Search:

- `search` over `id,name,bin`

Ordering:

- `ordering=name` or `ordering=id`

Response (200 non-paginated):

```json
{
  "success": true,
  "data": [
    {
      "name": "Head Office",
      "guid_1c": "ORG-GUID-001",
      "bin": "123456789012"
    }
  ],
  "error": []
}
```

### 11.4.3 Retrieve / PATCH / DELETE

Path:

- `/api/v1/employee-organization/{guid_1c}/`

PATCH body:

```json
{
  "name": "Head Office Updated",
  "bin": "123456789099"
}
```

PATCH response (200):

```json
{
  "success": true,
  "id": 30,
  "data": {
    "name": "Head Office Updated",
    "guid_1c": "ORG-GUID-001",
    "bin": "123456789099"
  },
  "error": []
}
```

DELETE response:

- HTTP 204 No Content (empty body)

---

## 11.5 Organization (`/api/v1/organization/`)

Lookup field: `id` (default)

### 11.5.1 Create (POST)

Body:

```json
{
  "name": "Main Organization",
  "full_name": "Main Organization LLP",
  "guid_1c": "ORG1C-001",
  "kbe": 17,
  "bin": "123456789012",
  "okpo": "1234567890"
}
```

Response (201, DRF default ModelViewSet):

```json
{
  "id": 40,
  "time_create": "2026-04-21T10:00:00Z",
  "time_update": "2026-04-21T10:00:00Z",
  "name": "Main Organization",
  "full_name": "Main Organization LLP",
  "guid_1c": "ORG1C-001",
  "kbe": 17,
  "bin": "123456789012",
  "okpo": "1234567890"
}
```

### 11.5.2 List (GET)

Filters:

- `name`
- `bin`
- `guid_1c`

Ordering:

- `ordering=id|name|bin`

Response: standard DRF paginated list (`count/next/previous/results`) where `results` is array of objects.

### 11.5.3 Retrieve / PUT / PATCH / DELETE

Paths:

- `/api/v1/organization/{id}/`

PUT/PATCH body: same fields as create (all or partial).

Responses:

- GET/PUT/PATCH: standard DRF object JSON
- DELETE: HTTP 204 No Content

---

## 11.6 Employee Identification (related but often required)

Endpoint:

- `/api/v1/employee-identification/` (POST)

Write serializer accepted fields:

- `auth_time` (optional)
- `location` (optional, write-only)
- `employee` (optional)
- `employeeNo` (optional)

Practical note:

- Real flow also accepts terminal payload formats (multipart/json/xml) and transforms internally.
- Successful processing returns plain body `OK` with HTTP 200.

Additional actions:

- `/api/v1/employee-identification/missing/`
- `/api/v1/employee-identification/organization-period/`

---

## 11.7 Error/Status conventions summary

- Custom employee/position/division/employee-organization endpoints: JSON envelope with `success`/`data`/`error` for read/update, and `id`/`message` for create.
- Delete on these endpoints returns 204 empty body in actual runtime.
- Organization endpoint uses default DRF JSON (no custom envelope).
- Employee create/update validation errors return DRF field error objects.
