# Requirements Checklist

Этот документ фиксирует соответствие реализованных проектов формулировкам кейс-задач. Дальнейшая разработка должна добавлять только функции, которые есть в этом чеклисте или технически необходимы для их работы.

## Кейс-задача 3. Блог

| Требование ТЗ | Реализация |
| --- | --- |
| Создать web-страницу | `case_03_blog/app/templates/index.html`, `case_03_blog/app/static/css/style.css` |
| Регистрация/вход пользователя | `case_03_blog/app/main.py`: `/register`, `/login`, `/logout` |
| Написание своего поста | `case_03_blog/app/main.py`: `/posts` |
| Подписка на пользователей | `case_03_blog/app/main.py`: `/users/{author_id}/subscribe`, `/users/{author_id}/unsubscribe` |
| Генерация списка на основе подписок | `case_03_blog/app/main.py`: `/feed` |
| Просмотр публичных постов | `case_03_blog/app/main.py`: `/` |
| Скрытый пост "только по запросу" | `case_03_blog/app/main.py`: `/private`, `/posts/{post_id}/request-access`, `/access-requests/{request_id}/approve`, `/access-requests/{request_id}/reject` |
| Редактирование/удаление поста | `case_03_blog/app/main.py`: `/posts/{post_id}/edit`, `/posts/{post_id}/delete` |
| Добавление и сортировка постов по тегам | `case_03_blog/app/main.py`: `parse_tags`, параметр `tag`, параметр `sort` |
| Комментарии к постам | `case_03_blog/app/main.py`: `/posts/{post_id}/comments`, `/comments/{comment_id}/delete` |
| Анализ выполненной задачи не менее 7 пунктов | `case_03_blog/docs/analysis.md` |
| Рекомендации по устранению ошибок | `case_03_blog/docs/analysis.md` |
| Ссылка на GitHub-репозиторий | `https://github.com/adzheliev/synergy-practicum-3rd-course` |

## Кейс-задача 4. Книжный магазин

| Требование ТЗ | Реализация |
| --- | --- |
| Создать web-страницу | `case_04_bookstore/app/main.py`, `case_04_bookstore/app/static/css/style.css` |
| Создать 2 интерфейса: администратора и пользователя | `case_04_bookstore/app/main.py`: роль `admin`, роль `user` |
| Создать базу данных любимых книг | `case_04_bookstore/app/models.py`: `Book`, `Category`; `case_04_bookstore/app/seed.py` |
| Просмотр книги из библиотеки | `case_04_bookstore/app/main.py`: каталог на `/` |
| Сортировка по категории | `case_04_bookstore/app/main.py`: параметр `category` |
| Сортировка по автору | `case_04_bookstore/app/main.py`: `sort=author` |
| Сортировка по году написания | `case_04_bookstore/app/main.py`: `sort=year` |
| Покупка книги | `case_04_bookstore/app/main.py`: `/books/{book_id}/purchase` |
| Аренда на 2 недели / месяц / 3 месяца | `case_04_bookstore/app/main.py`: `/books/{book_id}/rent`, значения `14`, `30`, `90` |
| Изменение списка книг администратором | `case_04_bookstore/app/main.py`: `/admin/books` |
| Управление ценой | `case_04_bookstore/app/main.py`: `/admin/books/{book_id}/update` |
| Управление статусом и доступностью | `case_04_bookstore/app/main.py`: `/admin/books/{book_id}/update` |
| Автоматические напоминания об окончании аренды | `case_04_bookstore/app/main.py`: `/admin/rental-reminders` |
| Анализ выполненной задачи не менее 7 пунктов | `case_04_bookstore/docs/analysis.md` |
| Рекомендации по устранению ошибок | `case_04_bookstore/docs/analysis.md` |
| Ссылка на GitHub-репозиторий | `https://github.com/adzheliev/synergy-practicum-3rd-course` |

## Кейс-задача 5. Дневник путешествий

| Требование ТЗ | Реализация |
| --- | --- |
| Создать web-сайт на любом стеке Web-разработки | `case_05_travel_diary/app/main.py`, `case_05_travel_diary/app/static/css/style.css` |
| Создать пользователя системы | `case_05_travel_diary/app/main.py`: `/register`, `/login`, `/logout` |
| Запись своего путешествия | `case_05_travel_diary/app/main.py`: `/trips` |
| Просмотр путешествий других пользователей | `case_05_travel_diary/app/main.py`: публичная лента `/` |
| Местоположение с геопозицией | `case_05_travel_diary/app/models.py`: `location`, `latitude`, `longitude`; форма `/trips` |
| Изображение мест | `case_05_travel_diary/app/models.py`: `TripImage`; форма `/trips` |
| Стоимость путешествия | `case_05_travel_diary/app/models.py`: `cost`; форма `/trips` |
| Места культурного наследия | `case_05_travel_diary/app/models.py`: `heritage_places`; форма `/trips` |
| Места для посещения | `case_05_travel_diary/app/models.py`: `places_to_visit`; форма `/trips` |
| Оценка удобства передвижения / безопасности / населенности / растительности | `case_05_travel_diary/app/models.py`: `TripRating`; форма `/trips` |
| Анализ выполненной задачи не менее 7 пунктов | `case_05_travel_diary/docs/analysis.md` |
| Рекомендации по устранению ошибок | `case_05_travel_diary/docs/analysis.md` |
| Ссылка на GitHub-репозиторий | `https://github.com/adzheliev/synergy-practicum-3rd-course` |

## Не добавлять без отдельного решения

- Лайки, рейтинги постов, поиск по всему сайту, социальные профили сверх подписок.
- Комментарии к путешествиям, карта с внешним API, загрузка файлов в облако.
- История административных действий, платежная интеграция, email-рассылка.
- Любые функции, которых нет в таблицах выше.

