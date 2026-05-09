# Backend Logging Improvement Plan

**Author**: Senior Backend Developer Review  
**Date**: 2026-05-10  
**Status**: AWAITING APPROVAL

---

## 1. Current State — Problems Found

### 1.1 No LOGGING config in settings.py
Django is running with default logging setup. There is **no** `LOGGING` dictionary in `core/settings.py`. This means:
- No log files on disk
- No log format control
- No log level separation
- No rotation

### 1.2 Logging coverage gaps
Only `coupon_dispatch` module has logger usage. All others have zero:

| Module | Logger Present |
|--------|---------------|
| `coupon_dispatch` | ✅ Partial |
| `notifications/services/` | ❌ Missing |
| `notifications/tasks.py` | ❌ Missing |
| `bonus_transactions/services/` | ❌ Missing |
| `bonus_transactions/tasks.py` | ❌ Missing |
| `amplitude/services/` | ❌ Missing |
| `amplitude/tasks.py` | ❌ Missing |
| `utils/amplitude_client.py` | ❌ Missing |
| `utils/avatariya_client.py` | ❌ Missing |
| `utils/mobile_client.py` | ❌ Missing |

### 1.3 Russian text in error strings (violates clean code principle)
Backend code should be 100% English. Russian found in:

```python
# notifications/serializers.py
'Excel файл должен быть .xlsx/.xlsm/.xltx/.xltm'
'Укажите хотя бы один корректный номер'
'Выберите город'
'Некорректный номер в строке {row_index}: {raw}'

# amplitude/management/commands/
raise CommandError('--start должна быть <= --end')
raise CommandError('Неверный формат даты: ...')
```

### 1.4 Error messages are free-form English text (not machine-readable)
`error_message` field in job results stores raw strings like:
```
"Phone is empty"
"Phone must be in 11-digit format and start with 7"
"Duplicate phone in input"
"Assign API failed: ..."
"Guest not found by phone"
```
These are shown directly to the end user on the frontend. They are not localized and not machine-readable.

### 1.5 No structured logging (`extra` dict)
Only one place in the entire project uses `extra={}` in a logger call. Most logs are plain string format with `%s` substitution but no structured metadata.

---

## 2. Target State — What We Will Build

### 2.1 Structured LOGGING config in settings.py

```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] [{levelname}] [{name}] {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"level": "WARNING", "propagate": True},
        "django.request": {"level": "ERROR", "propagate": True},
        "celery": {"level": "INFO", "propagate": True},
        "coupon_dispatch": {"level": "DEBUG", "propagate": True},
        "notifications": {"level": "DEBUG", "propagate": True},
        "bonus_transactions": {"level": "DEBUG", "propagate": True},
        "amplitude": {"level": "DEBUG", "propagate": True},
        "utils": {"level": "DEBUG", "propagate": True},
    },
}
```

**Why console-only?**  
The project runs in Docker. Docker captures stdout/stderr — log files inside containers are an anti-pattern. In production, Docker logs are collected by log drivers (CloudWatch, Loki, Datadog, etc.).

### 2.2 Standard log format for every service

Every service method follows this pattern:

```python
import logging
logger = logging.getLogger(__name__)

# Entry point log
logger.info("job_started", extra={"job_id": job.id, "mode": job.dispatch_mode})

# Progress log (when processing many items)
logger.debug("processing_row", extra={"job_id": job.id, "phone": phone, "row": index})

# Success log
logger.info("job_finished", extra={"job_id": job.id, "sent": sent, "errors": errors})

# Recoverable error (row skipped, not job failure)
logger.warning("row_skipped", extra={"job_id": job.id, "reason": "invalid_phone", "phone": phone_raw})

# Fatal error with full traceback
logger.exception("job_failed", extra={"job_id": job.id})
```

**Rules**:
- Log **message** is a short `snake_case` event name, not a sentence (machine-readable)
- **Details go in `extra`**, not in the message string
- Use `logger.exception()` inside `except` blocks — it auto-includes the traceback
- Never use `logger.error()` for caught exceptions — use `logger.exception()`
- Log level semantics:
  - `DEBUG` — row-level processing details
  - `INFO` — job lifecycle events (started, finished)
  - `WARNING` — recoverable issues (bad row, API timeout retried)
  - `ERROR` — job completed but with unexpected state
  - `EXCEPTION` — unhandled exception caught

### 2.3 Machine-readable error codes for job results

Replace free-form error strings with short `snake_case` error codes stored in the database. The frontend translates them to Russian for the user.

| Old `error_message` | New `error_code` |
|---------------------|-----------------|
| `"Phone is empty"` | `"phone_empty"` |
| `"Phone must be in 11-digit format and start with 7"` | `"invalid_phone_format"` |
| `"Duplicate phone in input"` | `"duplicate_phone"` |
| `"Assign API failed: ..."` | `"assign_api_error"` |
| `"Coupon was not assigned"` | `"coupon_not_assigned"` |
| `"Mobile coupon API failed: ..."` | `"mobile_api_error"` |
| `"Guest not found by phone"` | `"guest_not_found"` |
| `"Invalid phone number: ..."` | `"invalid_phone_format"` |

**Implementation approach**: The `error_message` field in the model keeps its name, but we store the error code (short English snake_case) instead of a sentence. We also keep a separate `error_detail` field for technical details (logged to log system only, not returned to frontend).

### 2.4 Clean serializer validation messages
All serializer `raise ValidationError(...)` and validator messages must be in English:

```python
# ❌ Before
raise serializers.ValidationError('Укажите хотя бы один корректный номер')

# ✅ After
raise serializers.ValidationError({'phone_numbers': 'At least one valid phone number is required.'})
```

---

## 3. Files to Change

### 3.1 `core/settings.py`
- **Change**: Add `LOGGING` dictionary (shown above)
- **Risk**: None — additive change

### 3.2 `coupon_dispatch/services/coupon_dispatch_service.py`
- **Change 1**: Replace `error_message` string values with error codes
  - `'Duplicate phone in input'` → `'duplicate_phone'`
  - `'Phone is empty'` → `'phone_empty'`
  - `'Phone must be in 11-digit format...'` → `'invalid_phone_format'`
  - `f'Assign API failed: {exc}'` → `'assign_api_error'`
  - `'Coupon was not assigned'` → `'coupon_not_assigned'`
  - `f'Mobile coupon API failed: {exc}'` → `'mobile_api_error'`
- **Change 2**: Log technical exception detail (the `str(exc)`) at `logger.warning` level — NOT stored in DB
- **Change 3**: Add `logger.debug()` per-row processing logs

### 3.3 `bonus_transactions/services/bonus_transaction_service.py`
- **Change 1**: Add `logger = logging.getLogger(__name__)` at top
- **Change 2**: Add job lifecycle logs (started, finished, failed)
- **Change 3**: Replace `error_message` with error codes:
  - `'Invalid phone number: ...'` → `'invalid_phone_format'`
  - `'Guest not found by phone'` → `'guest_not_found'`
  - `str(exc)` → `'processing_error'`

### 3.4 `bonus_transactions/tasks.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + task start/end logs

### 3.5 `notifications/services/push_dispatch_service.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + service method logs

### 3.6 `notifications/tasks.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + task start/end logs

### 3.7 `notifications/serializers.py`
- **Change**: Translate all Russian validation messages to English

### 3.8 `amplitude/services/` (all service files)
- **Change**: Add `logger = logging.getLogger(__name__)` + key operation logs

### 3.9 `amplitude/tasks.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + task start/end logs

### 3.10 `amplitude/management/commands/`
- **Change**: Translate Russian `CommandError` messages to English

### 3.11 `utils/avatariya_client.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + HTTP call logs (INFO level for start, WARNING for API errors)

### 3.12 `utils/mobile_client.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + HTTP call logs

### 3.13 `utils/amplitude_client.py`
- **Change**: Add `logger = logging.getLogger(__name__)` + sync operation logs

---

## 4. What Changes in Logs (Docker output)

### Before (messy, no context):
```
Starting coupon dispatch job task: job_id=49
Coupon dispatch job 49 started
Coupon dispatch job 49 finished: status=done assigned=2 errors=2
```

### After (structured, machine-readable):
```
[2026-05-10 02:05:12] [INFO] [coupon_dispatch.tasks] job_started {"job_id": 49, "task": "coupon_dispatch"}
[2026-05-10 02:05:12] [INFO] [coupon_dispatch.services.coupon_dispatch_service] job_processing_started {"job_id": 49, "mode": "predefined_coupon", "total_rows": 4}
[2026-05-10 02:05:12] [WARNING] [coupon_dispatch.services.coupon_dispatch_service] row_skipped {"job_id": 49, "row": 1, "reason": "phone_empty"}
[2026-05-10 02:05:12] [WARNING] [coupon_dispatch.services.coupon_dispatch_service] row_skipped {"job_id": 49, "row": 2, "reason": "invalid_phone_format", "phone_raw": "00058419"}
[2026-05-10 02:05:13] [INFO] [utils.mobile_client] api_call_success {"endpoint": "/api/prizes/order-coupon-info/bulk-create/", "phone": "77085702556"}
[2026-05-10 02:05:13] [INFO] [utils.mobile_client] api_call_success {"endpoint": "/api/prizes/order-coupon-info/bulk-create/", "phone": "77712822614"}
[2026-05-10 02:05:13] [INFO] [coupon_dispatch.services.coupon_dispatch_service] job_finished {"job_id": 49, "sent": 2, "errors": 2, "duration_s": 1.2}
```

---

## 5. Scope — What We Are NOT Changing

- Database migrations for job result models — error codes go in the existing `error_message` field (no schema change needed)
- Celery task retry logic — not in scope
- External logging systems (Sentry, Datadog) — not in scope for this project
- `amplitude/views.py` English ValidationError messages — already correct English, no change needed

---

## 6. Implementation Order

1. `core/settings.py` — LOGGING config (5 min)
2. `coupon_dispatch/services/coupon_dispatch_service.py` — error codes + logging (30 min)
3. `bonus_transactions/services/` + `tasks.py` — add logger + error codes (20 min)
4. `notifications/services/` + `tasks.py` + `serializers.py` — add logger + translate Russian (15 min)
5. `amplitude/services/` + `tasks.py` + `management/commands/` — add logger + translate Russian (20 min)
6. `utils/` (3 client files) — add HTTP call logging (15 min)

**Total estimated backend work**: ~2 hours
