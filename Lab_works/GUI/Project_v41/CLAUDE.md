# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive web map of the Moscow Railway (МЖД — Московская Железная Дорога), built as a single self-contained HTML file using Leaflet.js.

## Running the Project

Open `index_2.html` directly in a browser, or serve with a local HTTP server (required for the Yandex Schedule API due to CORS):

```bash
python3 -m http.server 8080
# then open http://localhost:8080/index_2.html
```

## Regenerating Data

Full pipeline (run from `Project_v41/`):

```bash
# 1. Скачать актуальные координаты из OSM (нужен интернет, ~1–2 мин)
python3 tools/fetch_osm_railway.py   # → osm_lookup.json (в .gitignore)

# 2. Сгенерировать данные (OSM как приоритет, интерполяция как fallback)
python3 gen_mjd.py                   # → _generated_infra.json (в .gitignore)

# 3. Обновить JS-файл данных
python3 -c "
import json
with open('_generated_infra.json', encoding='utf-8') as f:
    data = json.dumps(json.load(f), ensure_ascii=False)
with open('mjd_infra_data.js', 'w', encoding='utf-8') as f:
    f.write('const MJD_INFRA = ' + data + ';')
print('mjd_infra_data.js обновлён')
"
```

`gen_mjd.py` использует `osm_lookup.json` для точных координат (77%+ объектов). Объекты с `snap: false` не смещаются к линиям в браузере.

```bash
# 4. Скачать полную сеть МЖД (пути + все станции из OSM, ~5–8 мин)
python3 tools/fetch_mjd_network.py   # → mjd_osm_network.js (в .gitignore)
```

`mjd_osm_network.js` (~1.8 МБ) содержит `MJD_OSM_NETWORK` (6399 участков, 84k точек) и `MJD_OSM_STATIONS` (2934 станции/платформы с именами). Файл в `.gitignore` — регенерировать при обновлении данных OSM.

## Architecture

### Data Flow

```
gen_mjd.py → _generated_infra.json → (manual) → mjd_infra_data.js
                                                        ↓
                                               index_2.html (loads via <script>)
```

### index_2.html Structure

All application code lives in one file, divided into sections marked with `// ===== SECTION =====` comments:

| Section | Description |
|---|---|
| `ДАННЫЕ` | Hardcoded arrays: `STATIONS` (8 вокзалов + пригородные), `DEPOTS`, `FREIGHT`, `SORTING`, `TERMINALS`, `MCC_STA` (31 МЦК) |
| `ГЕОМЕТРИЯ` | Catmull-Rom spline smoothing (`smoothPolyline`), snap-to-line (`snapObjectsToPolylines`) |
| `КАРТА` | Leaflet map init, tile layer, theme switching |
| `СЛОИ` | `LG` object — one `L.layerGroup` per object type |
| `ЛИНИИ НА КАРТЕ` | OSM rail network (`LG.osmNetwork`), OSM stations (`LG.osmStations`), МЦК ring, Большое кольцо, 10 radial polylines in `RADIALS_RAW`, МЦД (from `mjd_tracks_data.js`) |
| `ИКОНКИ` | `mkIcon()`, `mkStationIcon()`, etc. |
| `МАРКЕРЫ` | `addMarkers(arr)` — adds all objects to their layer groups |
| `INFO PANEL` | `openInfoPanel()`, `renderTab()`, `renderParams/Live/Sched()` |
| `ЯНДЕКС API` | `fetchYandexSchedule()` with 5-min cache, used for 8 main stations |
| `ФИЛЬТРЫ` | Checkbox → show/hide `LG` layer groups |
| `ПОИСК` | Filters `ALL` array (union of all object arrays) |
| `СТАТУС-СТРОКА` | МСК time, cursor coords, zoom, object count |

### Key Global Variables

- `RADIALS_RAW` — array of `{name, color, coords[]}` for 10 radial directions; smoothed into `RADIALS`
- `BIG_RING_RAW` / `BIG_RING` — Большое кольцо raw coords / smoothed
- `MJDLINES_FOR_SNAP` — all polylines used as snap targets for marker positioning
- `ALL` — flat union of every object array; used for search and `ОБЪЕКТОВ:` counter
- `markerMap` — `{id → {marker, data}}` for flyTo on search result click
- `LG` — `{type → L.layerGroup}` — all visible layers
- `MJD_INFRA` — loaded from `mjd_infra_data.js`; split into `INFRA_PASS`, `INFRA_HALT`, `INFRA_NODE`, etc.
- `MJD_MCD` — loaded from `mjd_tracks_data.js`; МЦД route polylines D1–D4
- `MJD_OSM_NETWORK` / `MJD_OSM_STATIONS` — loaded from `mjd_osm_network.js` (gitignored); full rail network and all named stations from OSM

### Object Schema

Every map object follows:
```js
{ id, type, name, lat, lng, desc, stats: {key: value, ...}, sched?: [[time, dest, platform], ...] }
```
`type` must be one of: `station | depot | freight | sorting | terminal | mcc | pass | halt | node | depot_vag`

### Coordinate Snapping

After all polylines are built, **every** object (including hardcoded `STATIONS`) gets its `lat/lng` overwritten to the nearest point on `MJDLINES_FOR_SNAP`. This means hardcoded coordinates in data arrays are only approximate starting positions — real rendered positions depend on the polyline geometry.

## Git Workflow — обязательно после каждого изменения

Репозиторий: `origin` → `https://github.com/iliyakolesnikov/MGD.git`  
Git-корень: `/home/s/Proga/Lab_works/GUI/` (на уровень выше `Project_v41/`).

**После каждого изменения файлов проекта** выполнять из git-корня:

```bash
git add Project_v41/<изменённые файлы>
git commit -m "<короткое описание>"
git push origin main
```

### Правила коммитов

- Коммитить только файлы проекта (`Project_v41/`), не трогать другие папки репозитория.
- Одно логическое изменение = один коммит. Не группировать несвязанные правки.
- Сообщение коммита: **на русском, одна строка, конкретно** — что именно изменилось. Примеры:
  - `добавить точные координаты Казанского направления`
  - `исправить трассу Рижского направления`
  - `добавить остановки Горьковского хода`
  - `обновить mjd_infra_data.js после перегенерации`
- Не использовать расплывчатые сообщения типа "fix", "update", "изменения".

### Что коммитить

| Файл | Когда |
|---|---|
| `index_2.html` | при любом изменении логики, данных или стилей |
| `mjd_infra_data.js` | после регенерации через `gen_mjd.py` |
| `gen_mjd.py` | при изменении генератора |
| `CLAUDE.md` | при изменении этого файла |

`_generated_infra.json` — промежуточный файл, его **не коммитить**.

### Откат к предыдущей версии

```bash
git log --oneline                                          # посмотреть историю
git checkout <hash> -- Project_v41/index_2.html           # откатить один файл
git push origin main                                       # сохранить откат в remote
```

## Актуализация этого файла

При каждом изменении архитектуры проекта — **обновить CLAUDE.md в том же коммите**:
- новые файлы или папки → добавить в секцию «Новые файлы»
- новый тип объекта на карте → добавить в «Object Schema»
- новый слой или инструмент → добавить в таблицу секций `index_2.html`
- изменение git-процесса или команд сборки → обновить соответствующий раздел

## Improvement Goals (from project plan)

1. Replace approximate interpolated coordinates in `gen_mjd.py` with accurate real-world coordinates
2. Replace the rough `RADIALS_RAW` corridor lines with geometrically accurate railway track polylines connecting real station positions
