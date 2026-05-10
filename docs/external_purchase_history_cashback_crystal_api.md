# API Документация: История покупок, Cashback и Crystals

## 1. Назначение

Документ описывает, как внешнему сервису получить:
1. Заказы.
2. Позиции заказа (items).
3. Платежи по заказу.
4. Данные парка.
5. Текст истории покупок.
6. Текущие балансы cashback и crystals.
7. Истории операций cashback и crystals.

Базовый префикс API: `/api/v1/`

Аутентификация: проектная DRF-аутентификация (Bearer/Basic).

## 2. Общие правила ответов

Для list-эндпоинтов используется стандартная DRF-пагинация:
1. `count`: общее количество записей.
2. `next`: ссылка на следующую страницу.
3. `previous`: ссылка на предыдущую страницу.
4. `results`: массив объектов текущей страницы.

Параметры пагинации:
1. `page`: номер страницы.
2. `page_size`: размер страницы (если включен в настройках пагинации).

## 3. Рекомендуемая схема интеграции

### 3.1 Быстрый сценарий (рекомендуется)

Получить заказы сразу с вложенными items/payments и названием парка:
1. `GET /api/v1/order/read/`

Затем получить балансы и историю:
1. `GET /api/v1/cashback/summary/current/?guest=<guest_id>`
2. `GET /api/v1/crystal/summary/?guest=<guest_id>`
3. `GET /api/v1/cashback/?guest=<guest_id>&transaction_date__gte=<date>&transaction_date__lte=<date>`
4. `GET /api/v1/crystal/?guest=<guest_id>`

### 3.2 Классический сценарий (больше запросов)

Если нужно раздельно:
1. `GET /api/v1/order/`
2. `GET /api/v1/item/?order=<order_id>`
3. `GET /api/v1/payment/?order=<order_id>`
4. `GET /api/v1/park/<park_id>/`

## 4. Заказы для истории покупок

### 4.1 Эндпоинт

`GET /api/v1/order/read/`

Read-only endpoint, который уже включает:
1. Поля заказа.
2. Массив `items`.
3. Массив `payments`.
4. `park_name` и `guest_phone`.

### 4.2 Фильтры

Поддерживаемые query-параметры:
1. `guest`
2. `guid_1c`
3. `cause`
4. `park`
5. `source`
6. `payment_id`
7. `guest_phone` (contains)
8. `c_created_from` (datetime gte)
9. `c_created_to` (datetime lte)
10. `c_created_date` (date)
11. `product` (id продукта внутри items)
12. `updated_from` (time_update gte)
13. `source_in` (значения через запятую)
14. `point_of_sale_in` (значения через запятую)

Сортировка:
1. `ordering=id`
2. `ordering=c_created`
3. `ordering=time_create`
4. `ordering=time_update`

Сортировка по умолчанию:
1. `-c_created`
2. `-id`

### 4.3 Пример запроса

`GET /api/v1/order/read/?guest=250482&c_created_from=2026-04-01T00:00:00Z&c_created_to=2026-04-30T23:59:59Z`

### 4.4 Поля ответа заказа

Каждый объект заказа содержит:
1. `id`: внутренний id заказа.
2. `time_create`: дата/время создания записи.
3. `time_update`: дата/время обновления записи.
4. `guest_phone`: телефон гостя.
5. `c_created`: бизнес-дата/время заказа.
6. `source`: источник заказа.
7. `guid_1c`: GUID документа в 1C.
8. `cause`: дополнительный GUID причины (опционально).
9. `check_type`: тип чека (`1` продажа, `-1` возврат).
10. `waiter_name`: имя официанта (опционально).
11. `table_id`: id стола (опционально).
12. `fact_sum`: сумма заказа.
13. `register_shift`: номер смены.
14. `receipt_number`: номер чека.
15. `fiscal_id`: фискальный идентификатор.
16. `status`: статус чека (`0` отменен, `1` отложен, `2` выдан, `3` архивный).
17. `fiscal_link`: ссылка на фискальные данные (опционально).
18. `payment_id`: внешний id платежа (опционально).
19. `invoice_id`: id счета (опционально).
20. `document_photo`: фото документа.
21. `park`: id парка.
22. `park_name`: название парка.
23. `guest`: id гостя.
24. `guest_name`: имя гостя.
25. `cash_register`: id кассы.
26. `reservation`: id резервации (опционально).
27. `items`: вложенные позиции заказа.
28. `payments`: вложенные оплаты.
29. `visits`: связанные визиты.

### 4.5 Поля вложенного массива items

Каждый объект в `items` содержит:
1. `id`: id позиции.
2. `time_create`: дата/время создания.
3. `time_update`: дата/время обновления.
4. `order`: id заказа.
5. `name`: название позиции.
6. `price_without_discount`: цена до скидки.
7. `discount`: размер скидки по позиции.
8. `quantity`: количество.
9. `total_sum`: итог по позиции.
10. `product`: id продукта.
11. `product_name`: название продукта (read-only).

### 4.6 Поля вложенного массива payments

Каждый объект в `payments` содержит:
1. `id`: id оплаты.
2. `time_create`: дата/время создания.
3. `time_update`: дата/время обновления.
4. `amount`: сумма оплаты.
5. `cashback_amount`: сумма оплаты бонусами cashback (опционально).
6. `payment_type`: id типа оплаты.
7. `order`: id заказа.
8. `payment_type_name`: название типа оплаты (read-only).

### 4.7 Поля вложенного массива visits

Каждый объект в `visits` содержит:
1. `id`: id визита.
2. `time_create`: дата/время создания.
3. `time_update`: дата/время обновления.
4. `guest`: id гостя.
5. `source`: источник визита.
6. `park`: id парка.
7. `order`: id заказа.

## 5. Item API (отдельно)

### 5.1 Эндпоинт

`GET /api/v1/item/`

### 5.2 Фильтры

1. `name`
2. `order`
3. `product`

### 5.3 Поля ответа Item

1. `id`
2. `time_create`
3. `time_update`
4. `order`
5. `name`
6. `price_without_discount`
7. `discount`
8. `quantity`
9. `total_sum`
10. `product`
11. `product_name`

## 6. Payment API (отдельно)

### 6.1 Эндпоинт

`GET /api/v1/payment/`

### 6.2 Фильтры

1. `order`
2. `payment_type`

### 6.3 Поля ответа Payment

1. `id`
2. `time_create`
3. `time_update`
4. `amount`
5. `cashback_amount`
6. `payment_type`
7. `order`
8. `payment_type_name`

## 7. Park API

### 7.1 Эндпоинты

1. `GET /api/v1/park/`
2. `GET /api/v1/park/<id>/`

### 7.2 Фильтры

1. `park_name`
2. `city`
3. `guid_1c`
4. `active`

### 7.3 Поля ответа Park

1. `id`: id парка.
2. `time_create`: дата/время создания.
3. `time_update`: дата/время обновления.
4. `park_name`: название парка.
5. `city_remove`: legacy-поле города (строка).
6. `city`: id города.
7. `guid_1c`: GUID парка в 1C.
8. `address_ru`: адрес на русском.
9. `address_kz`: адрес на казахском.
10. `id_bitrix_24`: id в Bitrix24.
11. `active`: активность парка.
12. `iiko_organization_id`: внешний идентификатор iiko.
13. `menu_id`: идентификатор меню.

## 8. Cashback: баланс и история

### 8.1 История cashback (транзакции)

`GET /api/v1/cashback/`

Фильтры:
1. `transaction_date`
2. `transaction_date__gte`
3. `transaction_date__lte`
4. `guest`
5. `expiration_date`
6. `amount`
7. `doc_guid`
8. `base_id`
9. `guest__phone`

Поля транзакции cashback:
1. `id`
2. `time_create`
3. `time_update`
4. `guest`: id гостя.
5. `transaction_date`: дата/время операции.
6. `amount`: количество бонусов.
7. `expiration_date`: дата сгорания.
8. `start_date`: дата начала действия.
9. `doc_guid`: GUID документа операции.
10. `base_id`: внешний base id.
11. `park_id_deprecated`: устаревший идентификатор парка.
12. `park`: id парка.
13. `type`: тип операции (`1` начисление, `-1` списание).
14. `registration_bonus`: флаг регистрационного бонуса.
15. `source`: источник операции (опционально).

### 8.2 Текущий баланс cashback

`GET /api/v1/cashback/summary/current/?guest=<guest_id>`

Поля ответа:
1. `guest`: id гостя.
2. `sum`: текущий доступный баланс cashback.
3. `burn_date`: ближайшая дата сгорания.
4. `burn_sum`: сумма, которая сгорит в эту дату.

### 8.3 Сводка cashback по интервалам

`GET /api/v1/cashback/summary/?guest=<guest_id>&actual_for_date=<YYYY-MM-DD>`

Поля ответа:
1. `guest`
2. `start_date`
3. `expiration_date`
4. `sum`

Используйте этот endpoint, если нужно видеть корзины баланса по периодам действия.

## 9. Crystals: баланс и история

### 9.1 История crystals (транзакции)

`GET /api/v1/crystal/`

Фильтры:
1. `guest`
2. `park`
3. `doc_guid`
4. `type`

Поля транзакции crystal:
1. `id`
2. `time_create`
3. `time_update`
4. `date`: дата операции.
5. `guest`: id гостя.
6. `park`: id парка.
7. `amount`: изменение баланса (плюс/минус).
8. `doc_guid`: GUID документа операции.
9. `order`: id заказа (опционально).
10. `base_id`: внешний base id.
11. `description_ru`: описание на русском.
12. `description_kz`: описание на казахском.
13. `type`: тип операции (`0` подарок, `1` игра, `2` день рождения, `3` покупка).

### 9.2 Текущий баланс crystals

`GET /api/v1/crystal/summary/?guest=<guest_id>`

Поля ответа:
1. `guest`
2. `total_crystals`

## 10. Опционально: Reserve Crystal

Если в интеграции используется резервный контур кристаллов:
1. `GET /api/v1/reserve_crystal/`
2. `GET /api/v1/reserve_crystal/summary/?guest=<guest_id>`

Поля summary:
1. `guest`
2. `total_crystals`

## 11. Статус гостя (заблокирован/разблокирован/активный)

Если внешнему сервису нужно показывать статус гостя, используйте endpoint:
1. `GET /api/v1/guest/<guest_id>/`

Поле статуса в модели гостя:
1. `black_list`

Значения `black_list`:
1. `0` = `Неопределено`
2. `1` = `Заблокирован`
3. `2` = `Разблокирован`

Правило интерпретации для внешнего сервиса:
1. Если `black_list = 1`, статус гостя = `Заблокированный`.
2. Если `black_list = 2`, статус гостя = `Активный`.
3. Если `black_list = 0` (неопределено), статус гостя = `Активный`.

Итоговая проверка в коде интеграции:
1. `is_blocked = (black_list == 1)`
2. Во всех остальных случаях гость считается активным.

## 12. Пример сборки текста истории покупок

Шаги:
1. Получить список заказов через `/api/v1/order/read/` с фильтрами по гостю и периоду.
2. Для каждого заказа взять вложенные `items` и `payments`.
3. Взять `park_name` из заказа (или дополнительно запросить `/api/v1/park/<id>/` при необходимости).
4. Получить текущий cashback: `GET /api/v1/cashback/summary/current/?guest=<guest_id>`.
5. Получить текущий crystal: `GET /api/v1/crystal/summary/?guest=<guest_id>`.
6. Получить историю cashback: `GET /api/v1/cashback/?guest=<guest_id>&transaction_date__gte=...&transaction_date__lte=...`.
7. Получить историю crystals: `GET /api/v1/crystal/?guest=<guest_id>`.

Шаблон текстовой записи по заказу:
1. Дата: `c_created`
2. Парк: `park_name`
3. Сумма: `fact_sum`
4. Позиции: `items[].name`, `quantity`, `total_sum`
5. Оплаты: `payments[].payment_type_name`, `amount`

Отдельно добавить блок балансов:
1. Cashback: `sum`
2. Crystals: `total_crystals`

Если нужно добавить статус гостя в текст:
1. Получите `guest` из заказа (`/api/v1/order/read/`).
2. Запросите `/api/v1/guest/<guest_id>/`.
3. Примените правило: `black_list = 1` -> `Заблокированный`, иначе -> `Активный`.

## 13. Практические рекомендации

1. Для истории покупок используйте в первую очередь `/order/read/` для уменьшения числа запросов.
2. Для текущего cashback используйте `/cashback/summary/current/`.
3. Для текущего crystal используйте `/crystal/summary/`.
4. Для полной истории операций используйте `/cashback/` и `/crystal/`.
5. При фильтрации по датам и datetime придерживайтесь единой timezone-логики на стороне внешнего сервиса.
