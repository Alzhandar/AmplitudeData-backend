# Backend Code Style Canon (Amplitude)

## Purpose

This document defines mandatory backend coding conventions for this repository.
Use it as a checklist before implementation and as a contract for AI-assisted coding.

## 1. Work approach before coding

1. Inspect at least 2 existing modules with similar behavior before writing new code.
2. Reuse existing architectural patterns first, then extend.
3. Do not introduce a new style if an equivalent project style already exists.

## 2. Module architecture conventions

1. Transport client layer:
   - Keep external API calls in clients under utils/.
   - Client methods are thin transport wrappers.
   - Return safe parsed payloads (`dict` preferred; fallback `{'raw': parsed}` when needed).

2. Service layer:
   - Business rules and payload normalization live in services.
   - Service classes should accept dependencies via constructor for testability.
   - Upstream/service integration errors use explicit domain exception:
     - Pattern: `<Domain>UpstreamError`.

3. View layer:
   - Views validate input serializers, call services, and map exceptions to HTTP.
   - Avoid embedding business logic inside views.

## 3. Naming canon

1. Exceptions:
   - Service exceptions: `<Domain>UpstreamError`.
   - API gateway exceptions (DRF): `<Domain>GatewayUnavailable`.

2. APIException defaults:
   - Use explicit `status.HTTP_*` constants.
   - `default_code` must be stable snake_case and domain-specific.
   - Example: `mobile_registrations_gateway_unavailable`.

3. Methods:
   - For multi-argument methods in clients/services, prefer keyword-only style (`*`) for clarity.

4. Serializer names:
   - Query serializer: `<Domain>QuerySerializer`.
   - Response serializer: `<Domain>ResponseSerializer`.

## 4. Permissions and access control

1. If feature is page-scoped in frontend allowed_pages, add/use dedicated permission class.
2. Pattern:
   - `permission_classes = [IsAuthenticated, Has<Feature>Access]`.
3. Keep permission logic in `<app>/permissions.py`, not in views.

## 5. Error handling canon

1. Validation errors:
   - Raise DRF `ValidationError` with field-based detail when possible.

2. Upstream failures:
   - Catch domain `<Domain>UpstreamError` in view.
   - Log with `logger.exception(...)` and stable event-like message.
   - Raise `<Domain>GatewayUnavailable(...)` for 502 mapping.

3. Message policy:
   - Keep error messages concise and consistent.
   - Do not leak sensitive upstream internals.

## 6. Logging canon

1. Use module logger: `logger = logging.getLogger(__name__)`.
2. Use structured `extra={...}` for diagnostic fields (user_id, date range, entity id).
3. Log at the boundary where failure is translated to API response.

## 7. Tests canon

1. Every new endpoint requires:
   - serializer tests
   - service tests
   - view tests

2. Minimum view test cases:
   - success (200)
   - permission denied (403) if page-scoped
   - upstream failure mapping (502)

3. Run tests in the same environment as deployment workflow (for this project: Docker container).

## 8. Formatting and consistency

1. Match existing file formatting style (spaces/tabs, import grouping, quote style).
2. Keep naming and wording aligned with neighboring modules.
3. Avoid broad refactors in unrelated files while delivering a feature.

## 9. PR self-checklist

1. Did I copy the architecture pattern from existing modules?
2. Are permission classes aligned with allowed_pages policy?
3. Are exceptions named by canon and mapped to stable HTTP responses?
4. Are serializer/service/view tests present and passing?
5. Is logging structured and consistent?
6. Did I validate in Docker?

## 10. Prompt template for future AI tasks

Use this text when requesting backend implementation:

"Implement this in strict accordance with backend/docs/BACKEND_CODE_STYLE_CANON.md.
Before coding, inspect similar modules and follow existing project patterns for permissions,
service/view separation, naming, error mapping, logging, and tests.
Do not introduce a new style if a local convention already exists."
