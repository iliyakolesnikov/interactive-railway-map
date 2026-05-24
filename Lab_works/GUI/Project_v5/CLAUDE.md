# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive web map of the Moscow Railway (МЖД — Московская Железная Дорога). Two HTML files + shared config, no build step. Primary audience: МЖД workers (dispatchers, station masters, engineers). Secondary: passengers.

**Stations** are stored in Supabase (PostgreSQL). The map and admin panel connect via `config.js`.

## Running the Project

Open `MGD.html` directly in a browser (no local server needed — Supabase handles data):

```bash
python3 -m http.server 8080
# then open http://localhost:8080/MGD.html
# or open http://localhost:8080/admin.html
```

## Files

| Файл | Git | Описание |
|---|---|---|
| `MGD.html` | ✅ | Главная карта — Leaflet + Supabase |
| `admin.html` | ✅ | Управление станциями (CRUD) |
| `config.js` | ✅ | `SUPABASE_URL` + `SUPABASE_KEY` (anon) |
| `mjd_osm_network.js` | ✅ | Полная сеть МЖД: пути (~8 МБ) |
| `osm_lookup.json` | ❌ | Координаты из OSM (промежуточный файл) |
| `_generated_infra.json` | ❌ | Промежуточный вывод |

## Architecture

### MGD.html Structure

Sections marked with `// ===== SECTION =====`:

| Section | Description |
|---|---|
| `КАРТА` | Leaflet init, tile layer, `applyTheme()` |
| `СЛОИ` | `LG.osmNetwork` + `LG.mjdStations` |
| `ЛИНИИ НА КАРТЕ` | Рендер OSM-путей из `MJD_OSM_NETWORK` в `LG.osmNetwork`; direction-aware bridging разрывов ≤600 м |
| `РЕНДЕР СТАНЦИЙ И ОСТАНОВОК` | `renderStations(list)` — маркеры + тултипы из Supabase |
| `СТАНЦИИ МЖД НА КАРТЕ` | `loadFromDB()` — загрузка из Supabase, fallback на `MJD_OSM_NETWORK` |
| `ГРАНИЦА МОСКВЫ` | Контур города через Nominatim GeoJSON |
| `ПОИСК СТАНЦИЙ` | Live-поиск по `stationList` |
| `ФИЛЬТРЫ` | `saveFilters()` / `applyFilters()` с localStorage |
| `КНОПКИ КАРТЫ` | zoom +/−/reset, тема |
| `РЕСАЙЗ БОКОВЫХ ПАНЕЛЕЙ` | drag-resize сайдбаров |
| `СТАТУС-СТРОКА` | МСК время, координаты курсора, зум |

### Key Global Variables

- `LG` — `{ osmNetwork: L.layerGroup, mjdStations: L.layerGroup }` — два видимых слоя
- `MJD_OSM_NETWORK` — из `mjd_osm_network.js`; массив координат с `null`-разделителями сегментов
- `SUPABASE_URL`, `SUPABASE_KEY` — из `config.js`
- `stationList` — массив объектов `{id, name, lat, lon, type, line}` из Supabase
- `stationMarkers` — массив `L.marker` в `LG.mjdStations`

### Data Flow

```
mjd_osm_network.js ──────────────────────────────────────→ LG.osmNetwork (пути)
config.js (SUPABASE_URL/KEY) → Supabase DB → loadFromDB() → LG.mjdStations (станции)
```

`admin.html` читает/пишет станции напрямую в Supabase через `fetch()`.

## Git Workflow — обязательно после каждого изменения

Репозиторий: `origin` → `https://github.com/iliyakolesnikov/MGD.git`  
Git-корень: `/home/s/Proga/Lab_works/GUI/` (на уровень выше `Project_v5/`).

```bash
git add Project_v5/<изменённые файлы>
git commit -m "<короткое описание на русском>"
git push origin main
```

### Правила коммитов

- Коммитить только файлы проекта (`Project_v5/`).
- Одно логическое изменение = один коммит.
- Сообщение — одна строка, конкретно: `добавить поиск по направлениям`.
- Не использовать расплывчатые «fix», «update», «изменения».

### Что коммитить

| Файл | Когда |
|---|---|
| `MGD.html` | при любом изменении логики, данных или стилей карты |
| `admin.html` | при изменении панели управления |
| `config.js` | при смене Supabase-проекта |
| `mjd_osm_network.js` | после регенерации сети |
| `CLAUDE.md` | при изменении архитектуры проекта |

**Не коммитить:** `_generated_infra.json`, `osm_lookup.json`.

### Откат к предыдущей версии

```bash
git log --oneline
git checkout <hash> -- Project_v5/MGD.html
git push origin main
```

## Актуализация этого файла

При каждом изменении архитектуры проекта — **обновить CLAUDE.md в том же коммите**:
- новые файлы → добавить в таблицу «Files»
- новый слой → добавить в таблицы секций и Key Global Variables
- изменение data flow → обновить схему
