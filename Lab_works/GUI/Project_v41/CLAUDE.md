# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive web map of the Moscow Railway (МЖД — Московская Железная Дорога), built as a single self-contained HTML file using Leaflet.js. Primary audience: МЖД workers (dispatchers, station masters, engineers). Secondary: passengers.

## Running the Project

Open `index_2.html` directly in a browser, or serve with a local HTTP server (required for the Yandex Schedule API due to CORS):

```bash
python3 -m http.server 8080
# then open http://localhost:8080/index_2.html
```

`config.js` must exist (not committed, see below). Copy `config.example.js` → `config.js` and fill in the Yandex API key.

## Regenerating Data

Full pipeline (run from `Project_v41/`):

```bash
# 1. Скачать координаты станций из OSM (~1–2 мин)
python3 tools/fetch_osm_railway.py   # → osm_lookup.json (в .gitignore)

# 2. Сгенерировать инфра-объекты (OSM координаты как приоритет, интерполяция как fallback)
python3 gen_mjd.py                   # → _generated_infra.json (в .gitignore)

# 3. Обновить mjd_infra_data.js
python3 -c "
import json
with open('_generated_infra.json', encoding='utf-8') as f:
    data = json.dumps(json.load(f), ensure_ascii=False)
with open('mjd_infra_data.js', 'w', encoding='utf-8') as f:
    f.write('const MJD_INFRA = ' + data + ';')
print('mjd_infra_data.js обновлён')
"

# 4. Скачать трассы МЦД из OSM (relation IDs D1–D4)
python3 tools/fetch_osm_tracks.py    # → mjd_tracks_data.js (коммитить)

# 5. Скачать полную сеть МЖД: пути + все станции (~5–8 мин)
python3 tools/fetch_mjd_network.py   # → mjd_osm_network.js (в .gitignore)
```

### Файлы данных

| Файл | Размер | Git | Описание |
|---|---|---|---|
| `osm_lookup.json` | ~3 МБ | ❌ | Координаты 3597 объектов из OSM; источник для gen_mjd.py |
| `_generated_infra.json` | ~500 КБ | ❌ | Промежуточный вывод gen_mjd.py |
| `mjd_infra_data.js` | ~500 КБ | ✅ | 295 инфра-объектов с координатами и stats |
| `mjd_tracks_data.js` | ~180 КБ | ✅ | Трассы МЦД D1–D4 (5510 точек суммарно) |
| `mjd_osm_network.js` | ~1.8 МБ | ❌ | Полная сеть: 6399 участков (84k точек) + 2630 станций |
| `config.js` | мало | ❌ | Яндекс API ключ; скопировать из `config.example.js` |
| `config.example.js` | мало | ✅ | Шаблон конфига без ключа |

`gen_mjd.py`: 77%+ объектов получают точные OSM-координаты (`snap: false`). Остальные интерполируются вдоль линий (`snap: true`) и смещаются к ближайшей полилинии браузером.

## Architecture

### Data Flow

```
fetch_osm_railway.py → osm_lookup.json ─┐
                                        ├→ gen_mjd.py → _generated_infra.json → mjd_infra_data.js ─┐
fetch_osm_tracks.py  → mjd_tracks_data.js ──────────────────────────────────────────────────────────┤
fetch_mjd_network.py → mjd_osm_network.js ──────────────────────────────────────────────────────────┤
                                                                                                     ↓
                                                                                          index_2.html
```

### index_2.html Structure

All application code lives in one file, divided into sections marked with `// ===== SECTION =====` comments:

| Section | Description |
|---|---|
| `ДАННЫЕ` | Hardcoded arrays: `STATIONS` (8 вокзалов), `DEPOTS`, `FREIGHT`, `SORTING`, `TERMINALS`, `MCC_STA` (31 МЦК) |
| `ГЕОМЕТРИЯ` | `smoothPolyline()` — Catmull-Rom сглаживание; `snapObjectsToPolylines()` — привязка к линии; `snapOsmAware()` — пропускает объекты с `snap: false` |
| `КАРТА` | Leaflet map init, tile layer, `applyTheme()`, OpenRailwayMap tile toggle (`ormLayer`) |
| `СЛОИ` | `LG` object — один `L.layerGroup` на тип объекта |
| `ЛИНИИ НА КАРТЕ` | `LG.osmNetwork` (OSM пути), `LG.osmStations` (OSM станции), МЦК, Большое кольцо, 10 радиалей `RADIALS_RAW`, МЦД D1–D4 из `MJD_MCD` |
| `ИКОНКИ` | `mkIcon()`, `mkStationIcon()`, `mkMccIcon()` и др. |
| `МАРКЕРЫ` | `addMarkers(arr)` — добавляет объекты в layer groups |
| `INFO PANEL` | `openInfoPanel()`, `renderTab()`, `renderParams()` / `renderLive()` (DEMO-плашка) / `renderSched()` |
| `ЯНДЕКС API` | `fetchYandexSchedule()` с кэшем 5 мин; используется для 8 вокзалов |
| `ФИЛЬТРЫ` | `saveFilters()` / `applyFilters()` с localStorage; `LAYER_MAP` связывает `data-layer` с ключами LG |
| `ПОИСК` | `SEARCH_INDEX` (предкомпилированный); обработчик с debounce 200 мс |
| `ЗУМ-ВИДИМОСТЬ` | `updateZoomVisibility()` — скрывает halt/node/pass/osmStations на малых зумах |
| `СТАТУС-СТРОКА` | МСК время, координаты курсора, зум, счётчик объектов |

### Key Global Variables

- `RADIALS_RAW` — массив `{name, color, coords[]}` для 10 радиальных направлений; сглаживается в `RADIALS`
- `BIG_RING_RAW` / `BIG_RING` — Большое кольцо: исходный / сглаженный
- `MJDLINES_FOR_SNAP` — все полилинии для snap-привязки маркеров
- `ALL` — плоский union всех массивов объектов; используется для поиска и счётчика
- `markerMap` — `{id → {marker, data}}` для flyTo по клику в поиске
- `LG` — `{type → L.layerGroup}` — все видимые слои
- `MJD_INFRA` — из `mjd_infra_data.js`; разбивается на `INFRA_PASS`, `INFRA_HALT`, `INFRA_NODE` и др.
- `MJD_MCD` — из `mjd_tracks_data.js`; трассы D1–D4
- `MJD_OSM_NETWORK` / `MJD_OSM_STATIONS` — из `mjd_osm_network.js` (gitignored); полная сеть и 2630 станций/платформ без метро

### Object Schema

Every map object follows:
```js
{ id, type, name, lat, lng, desc, stats: {key: value, ...}, sched?: [[time, dest, platform], ...] }
```
`type` must be one of: `station | depot | freight | sorting | terminal | mcc | pass | halt | node | depot_vag`

### Coordinate Snapping

After all polylines are built, objects with `snap: true` get their `lat/lng` overwritten to the nearest point on `MJDLINES_FOR_SNAP`. Objects with `snap: false` (OSM-accurate coords from `osm_lookup.json`) are skipped by `snapOsmAware()`.

## Git Workflow — обязательно после каждого изменения

Репозиторий: `origin` → `https://github.com/iliyakolesnikov/MGD.git`  
Git-корень: `/home/s/Proga/Lab_works/GUI/` (на уровень выше `Project_v41/`).

```bash
git add Project_v41/<изменённые файлы>
git commit -m "<короткое описание на русском>"
git push origin main
```

### Правила коммитов

- Коммитить только файлы проекта (`Project_v41/`).
- Одно логическое изменение = один коммит.
- Сообщение — одна строка, конкретно: `добавить точные координаты Казанского направления`.
- Не использовать расплывчатые «fix», «update», «изменения».

### Что коммитить

| Файл | Когда |
|---|---|
| `index_2.html` | при любом изменении логики, данных или стилей |
| `mjd_infra_data.js` | после регенерации через `gen_mjd.py` |
| `mjd_tracks_data.js` | после регенерации через `fetch_osm_tracks.py` |
| `gen_mjd.py` | при изменении генератора |
| `tools/fetch_osm_railway.py` | при изменении скрипта |
| `tools/fetch_osm_tracks.py` | при изменении скрипта |
| `tools/fetch_mjd_network.py` | при изменении скрипта |
| `config.example.js` | при изменении структуры конфига |
| `CLAUDE.md` | при изменении архитектуры проекта |

**Не коммитить:** `_generated_infra.json`, `osm_lookup.json`, `mjd_osm_network.js`, `config.js`.

### Откат к предыдущей версии

```bash
git log --oneline
git checkout <hash> -- Project_v41/index_2.html
git push origin main
```

## Актуализация этого файла

При каждом изменении архитектуры проекта — **обновить CLAUDE.md в том же коммите**:
- новые файлы → добавить в таблицу «Файлы данных» и «Что коммитить»
- новый слой → добавить в таблицу секций и Key Global Variables
- новый инструмент → добавить в пайплайн
