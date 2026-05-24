# МЖД · Интерактивная карта железных дорог

Веб-карта Московской Железной Дороги (МЖД) на базе Leaflet.js и Supabase. Работает без сборки и локального сервера — достаточно открыть HTML-файл в браузере.

## Скриншот

> _Добавьте скриншот карты сюда_

## Возможности

- **Карта путей** — полная сеть МЖД из OpenStreetMap (~8 МБ, золотые линии)
- **Станции** — ~535 объектов из базы Supabase с разными иконками для станций и вокзалов
- **Подписи** — названия станций появляются при zoom ≥ 11
- **Поиск** — живой поиск по названию станции с переходом на карте
- **Фильтры** — фильтрация объектов, состояние сохраняется в localStorage
- **Темы** — тёмная и светлая тема оформления
- **Граница Москвы** — контур города через Nominatim
- **Панель управления** — CRUD-интерфейс для редактирования станций (`admin.html`)

## Структура проекта

```
Project_v5/
├── MGD.html              # Главная карта
├── admin.html            # Панель управления станциями
├── config.js             # Supabase URL + ключ
└── mjd_osm_network.js    # Сеть путей МЖД (OSM, ~8 МБ)
```

## Запуск

### Быстрый старт

1. Скопируйте `config.js` и заполните своими данными Supabase (см. раздел ниже)
2. Откройте `MGD.html` в браузере или запустите локальный сервер:

```bash
python3 -m http.server 8080
# Карта:   http://localhost:8080/MGD.html
# Админка: http://localhost:8080/admin.html
```

### Настройка Supabase

1. Зарегистрируйтесь на [supabase.com](https://supabase.com) (бесплатно)
2. Создайте проект и таблицу `stations`:

```sql
create table stations (
  id   bigint generated always as identity primary key,
  name text not null,
  lat  numeric not null,
  lon  numeric not null,
  type text,
  line text
);
```

3. Перейдите в **Settings → API** и скопируйте **Project URL** и **anon public key**
4. Вставьте их в `config.js`:

```js
const SUPABASE_URL = 'https://your-project.supabase.co';
const SUPABASE_KEY = 'your-anon-key';
```

## Технологии

| Компонент | Технология |
|---|---|
| Карта | [Leaflet.js](https://leafletjs.com/) 1.9.4 |
| Тайлы | CartoDB Dark / Light |
| База данных | [Supabase](https://supabase.com/) (PostgreSQL) |
| Фронтенд | Vanilla JS, без фреймворков и сборки |
| Шрифты | Rajdhani, Share Tech Mono (Google Fonts) |

## Репозиторий

```
https://github.com/iliyakolesnikov/MGD
```
