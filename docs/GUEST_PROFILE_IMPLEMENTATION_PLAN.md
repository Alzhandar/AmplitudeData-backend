# План реализации: страница «Информация о госте по номеру телефона»

## 1. Статус задачи

1. Отдельное Django-приложение создано: `guest_profile`.
2. Реализация функционала еще не начата.
3. Текущий документ описывает профессиональный план backend-реализации до старта кода.

## 2. Цель

Сделать единый backend API для новой страницы, куда пользователь вводит номер телефона и получает:
1. Статус гостя: активный или заблокированный.
2. Баланс бонусов (cashback).
3. Баланс кристаллов (crystals).
4. Историю покупок.
5. Историю открытия страниц в мобильном приложении.

## 3. Бизнес-требования и трактовка статуса

Согласно документации внешнего API:
1. Статус берется из `black_list` в `GET /api/v1/guest/<guest_id>/`.
2. `black_list = 1` означает «Заблокированный».
3. `black_list = 2` означает «Активный».
4. `black_list = 0` означает «Активный».

Итоговое правило backend:
1. `is_blocked = (black_list == 1)`.
2. Во всех остальных случаях статус считается активным.

## 4. Источники данных

### 4.1 Внешний Avatariya API

1. Поиск гостя по телефону: существующий метод `find_guest_by_phone` (в клиенте уже есть).
2. Статус гостя: `GET /api/v1/guest/<guest_id>/`.
3. История покупок: `GET /api/v1/order/read/?guest=<guest_id>`.
4. Cashback текущий: `GET /api/v1/cashback/summary/current/?guest=<guest_id>`.
5. Cashback история: `GET /api/v1/cashback/?guest=<guest_id>&transaction_date__gte=...&transaction_date__lte=...`.
6. Crystal текущий: `GET /api/v1/crystal/summary/?guest=<guest_id>`.
7. Crystal история: `GET /api/v1/crystal/?guest=<guest_id>`.

### 4.2 Локальная база (Amplitude)

Для блока «какие страницы открывал в мобильном приложении» используем таблицу `amplitude.MobileSession`:
1. `event_type`.
2. `event_time`.
3. `phone_number`.
4. `device_id`.
5. `platform`.

Важно:
1. В текущей схеме нет отдельного поля `screen_name`.
2. Поэтому первый релиз будет отдавать «историю мобильных событий/экранов» на основе `event_type`.
3. При необходимости можно ввести маппинг `event_type -> screen_title` (конфиг/словарь).

## 5. Архитектура (Clean Code + SOLID)

Новый модуль будет построен слоями.

### 5.1 Структура приложения

`guest_profile/`:
1. `apps.py`
2. `urls.py`
3. `permissions.py`
4. `serializers.py`
5. `views.py`
6. `services/guest_profile_service.py`
7. `services/external_guest_data_service.py`
8. `services/mobile_activity_service.py`
9. `types.py` (DTO/TypedDict/dataclass для внутреннего контракта)
10. `tests/` (unit + API)

### 5.2 Разделение ответственности

1. `views.py`:
   1. Только HTTP-уровень.
   2. Валидация query-параметров через serializer.
   3. Вызов orchestration-сервиса.

2. `guest_profile_service.py`:
   1. Оркестрация всех источников.
   2. Сбор итогового payload.
   3. Единая обработка частичных ошибок.

3. `external_guest_data_service.py`:
   1. Только обращения к AvatariyaClient.
   2. Нормализация внешних ответов в внутренние DTO.

4. `mobile_activity_service.py`:
   1. Только локальные запросы в `MobileSession`.
   2. Фильтрация по телефону/периоду.
   3. Группировка и пагинация событий.

### 5.3 SOLID в этом модуле

1. S (Single Responsibility): каждый сервис решает одну доменную задачу.
2. O (Open/Closed): новые внешние блоки (например reserve_crystal) добавляются новым сервис-адаптером без переписывания view.
3. L (Liskov): работа через явные интерфейсы/контракты DTO, без скрытых side-effects.
4. I (Interface Segregation): тонкие методы клиента, отдельные методы для summary/history/order.
5. D (Dependency Inversion): `GuestProfileService` получает зависимости через конструктор (AvatariyaClient, query service), легко мокается в тестах.

## 6. API-контракт нового endpoint

### 6.1 Endpoint

`GET /api/guest-profile/by-phone/`

Query-параметры:
1. `phone` (required).
2. `from_date` (optional, YYYY-MM-DD, для истории покупок/cashback/mobile).
3. `to_date` (optional, YYYY-MM-DD).
4. `orders_limit` (optional, default 20, max 100).
5. `mobile_events_limit` (optional, default 50, max 200).

### 6.2 Ответ

```json
{
  "phone": "77071234567",
  "guest": {
    "id": 250482,
    "name": "...",
    "status": {
      "code": "active",
      "label": "Активный",
      "black_list": 2,
      "is_blocked": false
    }
  },
  "balances": {
    "cashback": {
      "sum": 1200,
      "burn_date": "2026-06-01",
      "burn_sum": 200
    },
    "crystals": {
      "total_crystals": 80
    }
  },
  "purchase_history": {
    "count": 12,
    "results": [
      {
        "order_id": 1001,
        "created_at": "2026-04-10T12:33:00Z",
        "park_name": "...",
        "fact_sum": "12000.00",
        "items": [],
        "payments": []
      }
    ]
  },
  "cashback_history": {
    "count": 45,
    "results": []
  },
  "crystal_history": {
    "count": 20,
    "results": []
  },
  "mobile_activity": {
    "count": 30,
    "results": [
      {
        "event_time": "2026-05-01T10:20:00Z",
        "event_type": "open_home",
        "platform": "android",
        "device_id": "..."
      }
    ]
  },
  "warnings": []
}
```

### 6.3 Политика частичных ошибок

Если один из источников недоступен, endpoint не падает целиком:
1. Блок заполняется пустым списком/нулевым балансом.
2. В `warnings` добавляется машиночитаемый код, например `cashback_unavailable`.
3. HTTP статус остается `200`, если гость найден.
4. HTTP `404`, если гость по телефону не найден.
5. HTTP `400`, если номер невалидный.

## 7. Валидация и нормализация

1. Нормализовать номер в формат 11 цифр с префиксом `7`.
2. Поддержать ввод с `+7`, `8`, пробелами, дефисами.
3. Если формат невалидный, вернуть код ошибки `invalid_phone_format`.
4. `from_date` и `to_date` валидировать и ограничивать разумным диапазоном (например не более 365 дней).
5. Параметры limit ограничить верхними границами.

## 8. Безопасность и доступ

1. Endpoint под `IsAuthenticated`.
2. Добавить отдельный permission-класс `HasGuestProfileAccess` в стиле существующих модулей.
3. В `EmployeePortalPage` добавить новый код страницы, например `guest-profile`.
4. Доступ определять через текущий `EmployeeAccessService`.

## 9. Логирование и наблюдаемость

Структурированные логи на каждом шаге:
1. `guest_profile_request_started`.
2. `guest_profile_guest_found`.
3. `guest_profile_external_block_failed` с `block_name`.
4. `guest_profile_request_finished`.

В `extra` логов:
1. `request_id`.
2. `user_id`.
3. `phone` (маскированный).
4. `guest_id`.
5. `duration_ms`.

## 10. Изменения по файлам (план)

### 10.1 Конфигурация

1. Добавить `guest_profile` в `INSTALLED_APPS`.
2. Подключить `guest_profile.urls` в `core/urls.py`.

### 10.2 Новый модуль guest_profile

1. `urls.py`: route `/guest-profile/by-phone/`.
2. `serializers.py`: query serializer + response serializer.
3. `views.py`: `GuestProfileByPhoneView`.
4. `permissions.py`: `HasGuestProfileAccess`.
5. `services/*`: оркестрация и адаптеры.

### 10.3 Расширение клиента внешнего API

В `utils/avatariya_client.py` аккуратно добавить методы:
1. `list_orders_read(...)`.
2. `get_cashback_summary_current(...)`.
3. `list_cashback_transactions(...)`.
4. `get_crystal_summary(...)`.
5. `list_crystal_transactions(...)`.

С повторным использованием существующих механизмов пагинации и `_raise_for_status`.

## 11. План тестирования

### 11.1 Unit тесты

1. Нормализация телефона.
2. Маппинг `black_list -> status`.
3. Политика `warnings` при частичных ошибках.
4. Ограничения дат и limit.

### 11.2 Integration/API тесты

1. Успешный сценарий с полным payload.
2. Гость не найден.
3. Невалидный телефон.
4. Один внешний блок недоступен, ответ остается 200 с warnings.
5. Проверка permissions.

### 11.3 Регрессия

1. `docker compose exec -T web python manage.py check`.
2. Тесты нового app.
3. Smoke-проверка существующих endpoint модулей.

## 12. Этапы внедрения

1. Этап A: каркас app, urls, permission, query serializer.
2. Этап B: сервисы внешних данных и mobile activity.
3. Этап C: orchestration + единый response contract.
4. Этап D: тесты + логирование + финальная полировка ошибок.
5. Этап E: документация endpoint для frontend.

## 13. Риски и как закрываем

1. Риск: внешние API могут возвращать неполные данные.
   Решение: defensive parsing + warnings.
2. Риск: долгий ответ из-за большого числа запросов.
   Решение: лимиты, узкий период по умолчанию, легкая параллелизация независимых вызовов.
3. Риск: неоднозначность «страниц мобильного приложения».
   Решение: в v1 возвращаем события `event_type`, при необходимости добавляем словарь экранов.

## 14. Definition of Done

1. Endpoint работает по номеру телефона и возвращает все 5 бизнес-блоков.
2. Статус гостя корректно интерпретируется.
3. Частичные ошибки не роняют ответ целиком.
4. Есть unit + API тесты.
5. Логи структурированы и читаемы.
6. Frontend получает стабильный контракт.

## 15. Что делаем дальше

После вашего подтверждения начинаю реализацию строго по этому плану и поэтапно, с проверкой через Docker-команды проекта.
