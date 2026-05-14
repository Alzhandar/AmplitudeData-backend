# План реализации: статистика новых регистраций из Mobile API

## 1. Статус

1. Реализация еще не начата.
2. Документ описывает профессиональный backend-план до старта кода.
3. После согласования начинается реализация backend, затем frontend.

## 2. Цель

Добавить в backend интеграцию с Mobile API endpoint:

`GET /api/users/stats/new/?year=2026&start_date=2026-02-01&end_date=2026-02-03`

Ожидаемый upstream ответ:

```json
{
  "registrations": 1608,
  "total_users": 229796,
  "date_from": "2026-02-01",
  "date_to": "2026-02-03"
}
```

Бизнес-смысл: показывать, сколько было регистраций в мобильное приложение за выбранный период.

## 3. Архитектурный подход (Clean Code + SOLID)

1. Single Responsibility:
   - MobileClient отвечает только за transport и нормализацию ответа внешнего API.
   - Service-слой отвечает за бизнес-правила, валидацию и fallback.
   - View отвечает только за HTTP-уровень.
2. Open/Closed:
   - Новые метрики mobile API добавляются новыми методами и DTO без переписывания текущих endpoint.
3. Dependency Inversion:
   - Сервис принимает MobileClient через конструктор для тестируемости и mock/fake в unit tests.
4. Interface Segregation:
   - Узкий метод клиента для конкретного endpoint, без универсальных «супер-методов» бизнес-логики.

## 4. Контракт backend endpoint (для frontend)

### 4.1 Новый endpoint

`GET /api/amplitude/mobile-registrations-stats/`

Query params:
1. year (required, int, например 2026)
2. start_date (required, YYYY-MM-DD)
3. end_date (required, YYYY-MM-DD)

### 4.2 Ответ backend

```json
{
  "registrations": 1608,
  "total_users": 229796,
  "date_from": "2026-02-01",
  "date_to": "2026-02-03",
  "source": "mobile_api",
  "cached": false
}
```

Примечание: поля date_from/date_to сохраняются как в upstream для прозрачности контракта.

## 5. Изменения по backend файлам (план)

1. utils/mobile_client.py
   - Добавить метод get_new_user_registration_stats(year, start_date, end_date).
   - Внутри использовать существующий get(path, params).
   - Path: /api/users/stats/new/
   - Нормализовать и вернуть dict с ключами registrations, total_users, date_from, date_to.

2. amplitude/services/mobile_registrations_stats_service.py (новый файл)
   - Класс MobileRegistrationsStatsService.
   - Метод get_stats(year, start_date, end_date).
   - Проверка бизнес-ограничений:
     - start_date <= end_date
     - year совпадает с годом start_date и end_date, либо правило явно зафиксировано и логируется.
   - Нормализация чисел к int.
   - Формирование итогового payload для view.

3. amplitude/serializers.py
   - Добавить Query serializer для year/start_date/end_date.
   - Добавить Response serializer для registrations/total_users/date_from/date_to/source/cached.
   - Централизовать валидацию формата дат.

4. amplitude/views.py
   - Добавить MobileRegistrationsStatsViewSet (или APIView, если нужен узкий endpoint).
   - Permission: IsAuthenticated.
   - В list/get:
     - Валидация query serializer.
     - Вызов MobileRegistrationsStatsService.
     - Возврат Response.

5. amplitude/urls.py
   - Добавить route:
     - amplitude/mobile-registrations-stats/

6. Опциональный cache слой (рекомендуется)
   - Если endpoint будет часто вызываться с одинаковыми параметрами, добавить БД-кэш модель по паттерну LocationPresenceStatsCache:
     - поля: year, start_date, end_date, payload, updated_at
     - уникальность: year + start_date + end_date
   - В первой версии можно запустить без кэша, но документом предусмотреть расширение.

## 6. Валидация и правила

1. year
   - integer
   - диапазон, например 2020..2100
2. start_date/end_date
   - формат YYYY-MM-DD
   - start_date <= end_date
   - максимальный диапазон, например 366 дней
3. Согласованность year
   - Вариант A (строгий): year должен совпадать с годом обеих дат
   - Вариант B (гибкий): year передается в upstream как есть, а несогласованность пишется в warning log

Рекомендация для production: Вариант A, чтобы не принимать неоднозначные запросы.

## 7. Обработка ошибок

1. Ошибки валидации входа
   - HTTP 400
   - Ясные сообщения по полям
2. Ошибка внешнего Mobile API
   - HTTP 502
   - Сообщение: upstream mobile api unavailable
   - Детали upstream логировать только в backend logs
3. Таймаут внешнего API
   - HTTP 504 или 502 (выбрать единый стандарт в проекте)
4. Невалидный upstream payload
   - HTTP 502
   - Код ошибки: invalid_upstream_payload

## 8. Логирование и наблюдаемость

События:
1. mobile_registrations_stats_request_started
2. mobile_registrations_stats_upstream_called
3. mobile_registrations_stats_upstream_failed
4. mobile_registrations_stats_request_finished

В extra:
1. user_id
2. year
3. start_date
4. end_date
5. duration_ms
6. status_code

## 9. Тестовая стратегия

1. Unit tests: MobileRegistrationsStatsService
   - happy path
   - start_date > end_date
   - некорректный year
   - upstream вернул пустые/невалидные поля

2. Unit tests: serializer
   - формат дат
   - обязательность параметров
   - max range

3. API tests: view
   - 200 при валидных данных
   - 400 при невалидных query
   - 502 при upstream ошибке

4. Regression
   - убедиться, что существующие endpoint в amplitude не затронуты

## 10. План реализации по шагам

1. Добавить метод в MobileClient.
2. Добавить service слой с нормализацией и бизнес-валидацией.
3. Добавить serializers запроса/ответа.
4. Добавить view и route.
5. Написать unit/API тесты.
6. Прогнать тесты приложения amplitude.
7. Подготовить changelog и короткую инструкцию для frontend.

## 11. Критерии готовности (Definition of Done)

1. Endpoint работает и возвращает registrations/total_users/date_from/date_to.
2. Валидация входа полностью покрыта.
3. Ошибки upstream корректно маппятся на 502/стандартизованный ответ.
4. Есть тесты unit + API для нового функционала.
5. Код проходит линтеры и не ломает существующие endpoint.

## 12. Что делаем после вашего согласования

1. Реализую backend по плану с чистым кодом и тестами.
2. После вашего подтверждения backend-результата перейду к frontend интеграции по такому же профессиональному процессу.
