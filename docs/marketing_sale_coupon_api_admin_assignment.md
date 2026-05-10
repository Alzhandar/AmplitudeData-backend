# API маркетинговых акций и купонов + админка присвоения купонов

## 1) Базовые правила API

- Базовый префикс: /api/v1/
- Аутентификация: Bearer или Basic
- Пагинация: page size 50
- Общие query-параметры списка:
  - page: номер страницы
  - search: полнотекстовый поиск по search_fields
  - ordering: сортировка по ordering_fields

---

## 2) API получения маркетинговых акций

### 2.1 Список акций

- Метод: GET
- URL: /api/v1/marketing_sale/

Доступные фильтры:
- status: boolean (true/false)
- guid_1c: string

Поиск:
- search по полям:
  - name
  - status
  - guid_1c

Сортировка:
- ordering по полям:
  - id
  - status
- По умолчанию: id

Примеры запросов:
- /api/v1/marketing_sale/?status=true
- /api/v1/marketing_sale/?guid_1c=6be4e1d2-8a1d-4d8c-a4a4-2d58ab2d2e13
- /api/v1/marketing_sale/?search=скидка
- /api/v1/marketing_sale/?ordering=-id
- /api/v1/marketing_sale/?status=true&search=retail&page=2

### 2.2 Получение одной акции

- Метод: GET
- URL: /api/v1/marketing_sale/{id}/

### 2.3 Поля JSON маркетинговой акции

- id: integer, ID записи
- time_create: datetime, дата создания в Big Data
- time_update: datetime, дата последнего обновления
- name: string, название акции
- status: boolean, активна ли акция
- order_using: integer, внутренний порядок/приоритет использования
- guid_1c: string|null, GUID акции из 1C
- mobile: boolean, признак доступности для мобильного приложения
- type: string|null, тип скидки:
  - percentage
  - amount
- value: decimal, значение скидки (процент или сумма, зависит от type)

Пример JSON объекта:
{
  "id": 12,
  "time_create": "2026-04-20T12:10:01Z",
  "time_update": "2026-04-21T08:40:00Z",
  "name": "Весенняя акция",
  "status": true,
  "order_using": 1,
  "guid_1c": "6be4e1d2-8a1d-4d8c-a4a4-2d58ab2d2e13",
  "mobile": true,
  "type": "percentage",
  "value": "15.00"
}

---

## 3) API получения купонов

### 3.1 Список купонов

- Метод: GET
- URL: /api/v1/coupon/

Доступные фильтры:
- coupon: string, код купона
- marketing_sale: integer, ID маркетинговой акции
- status: integer
  - 0 = активен
  - 1 = применен
- park: integer, ID парка
- guest: integer, ID гостя
- guest__isnull: boolean, купон без гостя (свободный/не назначен)
- guest_isnull: boolean, alias для guest__isnull
- updated_from: datetime, фильтр по time_update >= updated_from

Поиск:
- search по полям:
  - coupon
  - guid_1c
  - marketing_sale

Сортировка:
- ordering по полям:
  - marketing_sale
  - status
  - park
  - guest
- По умолчанию: id

Примеры запросов:
- /api/v1/coupon/?status=0
- /api/v1/coupon/?marketing_sale=5&status=0
- /api/v1/coupon/?guest__isnull=true
- /api/v1/coupon/?updated_from=2026-04-01T00:00:00Z
- /api/v1/coupon/?search=A-1234-5678
- /api/v1/coupon/?ordering=-status
- /api/v1/coupon/?status=0&guest__isnull=true&ordering=id&page=1

### 3.2 Получение одного купона

- Метод: GET
- URL: /api/v1/coupon/{id}/

### 3.3 Поля JSON купона

- id: integer, ID записи
- time_create: datetime, дата создания
- time_update: datetime, дата обновления
- c_created: datetime, исходная дата создания купона
- marketing_sale: integer, ID маркетинговой акции
- coupon: string, код купона
- status: integer
  - 0 = активен
  - 1 = применен
- park: integer|null, ID парка использования
- order: integer|null, ID заказа, где купон применен
- valid_until: date|null, срок действия
- guid_1c: string|null, GUID купона из 1C
- guest: integer|null, ID гостя (кому назначен купон)
- mobile: boolean, read-only из marketing_sale.mobile

Пример JSON объекта:
{
  "id": 5301,
  "time_create": "2026-04-20T10:00:00Z",
  "time_update": "2026-04-21T08:45:00Z",
  "c_created": "2026-04-20T10:00:00Z",
  "marketing_sale": 5,
  "coupon": "A-1234-5678",
  "status": 0,
  "park": null,
  "order": null,
  "valid_until": "2026-12-31",
  "guid_1c": "1ad4f6b0-0f12-4a95-9d2f-110000000001",
  "guest": null,
  "mobile": true
}

---

## 4) API получения купонов в формате 1C

### 4.1 Список купонов (1C)

- Метод: GET
- URL: /api/v1/coupon/1c/

Фильтры и параметры:
- такие же, как у /api/v1/coupon/
  - coupon
  - marketing_sale
  - status
  - park
  - guest
  - guest__isnull
  - guest_isnull
  - updated_from
  - search
  - ordering
  - page

### 4.2 Поля JSON купона (1C)

- id: integer
- time_update: datetime
- c_created: datetime
- park_guid: string|null, guid_1c парка
- guid_1c: string|null, guid купона
- guest_guid: string|null, guid гостя
- order_guid: string|null, guid заказа
- marketing_sale_guid: string|null, guid маркетинговой акции
- coupon: string
- status: integer
- valid_until: date|null
- mobile: boolean

Пример JSON объекта:
{
  "id": 5301,
  "time_update": "2026-04-21T08:45:00Z",
  "c_created": "2026-04-20T10:00:00Z",
  "park_guid": null,
  "guid_1c": "1ad4f6b0-0f12-4a95-9d2f-110000000001",
  "guest_guid": null,
  "order_guid": null,
  "marketing_sale_guid": "9dbaf25f-9a3d-4d13-8f2d-220000000999",
  "coupon": "A-1234-5678",
  "status": 0,
  "valid_until": "2026-12-31",
  "mobile": true
}

---

## 5) Админка массового присвоения купонов

Сущность админки:
- BulkCouponAssignment

Что делает админка:
- Загружает Excel с телефонами
- Выбирает маркетинговую акцию
- Находит гостей по телефонам
- Назначает свободные купоны найденным гостям
- Отправляет результат в мобильное API
- Сохраняет подробную статистику и ошибки

### 5.1 Как админка показывает акции с доступными купонами

В форме выбора marketing_sale показываются только акции, где есть доступные купоны.

Условие доступного купона в форме:
- coupons.status = ACTIVE (0)
- coupons.guest is null
- coupons.valid_until >= today или coupons.valid_until is null

Дополнительно в UI рядом с названием акции показывается количество доступных купонов.

### 5.2 Как сервис реально выбирает свободные купоны для присвоения

При запуске обработки BulkCouponAssignmentService выбирает купоны так:
- marketing_sale = выбранная акция
- status = ACTIVE (0)
- guest is null
- valid_until >= today
- order by id

Важно:
- В реальном присвоении берутся только купоны с valid_until >= today.
- Купоны с valid_until = null форма может показать как доступные, но сервис присвоения их не берет.

### 5.3 Пошаговая логика присвоения

1. Статус операции переводится в processing.
2. Из Excel читается первый столбец с телефонами.
3. Телефоны нормализуются к формату 7XXXXXXXXXX.
4. По каждому телефону ищется Guest where phone=... and deleted=false.
5. Свободные купоны берутся списком по условиям выше.
6. Купоны назначаются гостям последовательно по порядку id.
7. Для каждого результата пишется BulkCouponAssignmentResult:
   - success=true или false
   - error_message при ошибке
8. После локального назначения вызывается отправка в мобильное API.
9. Заполняются поля mobile_api_sent, mobile_api_response, mobile_api_sent_at.
10. Финальный статус: completed или failed.

### 5.4 Как формируется JSON для мобильного API

Endpoint мобильного API:
- /prizes/order-coupon-info/bulk-create/

Метод:
- POST

Тело отправки:
{
  "coupons": [
    {
      "coupon": "A-1234-5678",
      "phone_number": "77071234567",
      "amount": "Код для посещения",
      "valid_until": "2026-12-31",
      "is_mobile": false,
      "icon": "https://api.example.com/media/coupon_icons/icon.png"
    }
  ]
}

Пояснение полей coupons[]:
- coupon: код купона
- phone_number: телефон получателя
- amount: текст для отображения в мобильном приложении (берется из name операции)
- valid_until: срок действия купона, если есть
- is_mobile: признак источника, отправляется false
- icon: абсолютный URL иконки, если иконка загружена

### 5.5 Какие поля статистики заполняются в BulkCouponAssignment

- total_phones: сколько телефонов в Excel
- guests_found: сколько гостей найдено
- available_coupons: сколько свободных купонов было на старте
- coupons_assigned: сколько купонов назначено
- errors_count: количество ошибок
- error_log: текст ошибок
- mobile_api_sent: успешно ли отправлено в мобильное API
- mobile_api_response: текст ответа мобильного API
- mobile_api_sent_at: время отправки в мобильное API
- status: pending, processing, completed, failed

---

## 6) Короткий чек для переноса в другой проект

1. Нужны модели MarketingSale, Coupon, BulkCouponAssignment, BulkCouponAssignmentResult.
2. Нужен API минимум:
   - GET /api/v1/marketing_sale/
   - GET /api/v1/coupon/
   - GET /api/v1/coupon/1c/
3. Нужна админ-форма, которая считает доступные купоны по условиям.
4. Нужен сервис присвоения с теми же фильтрами свободных купонов и логированием результатов.
5. Нужен клиент отправки в мобильный endpoint /prizes/order-coupon-info/bulk-create/.
