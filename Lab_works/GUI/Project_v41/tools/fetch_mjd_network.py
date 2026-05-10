#!/usr/bin/env python3
"""
Скачивает полную сеть МЖД из Overpass API:
  - все станции/платформы railway=station|halt
  - все железнодорожные пути railway=rail (usage=main|branch|regional)
Разбивает регион на сетку, чтобы не падать по таймауту.
Результат: mjd_osm_network.js

Запускать из Project_v41/:
    python3 tools/fetch_mjd_network.py
"""
import json, urllib.request, urllib.parse, sys, os, time

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def overpass(query, timeout_http=150, retry=2):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
          headers={"User-Agent": "MJD-map-project/1.0"})
    for attempt in range(retry + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_http) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f"  попытка {attempt+1} ошибка: {e}", file=sys.stderr)
            if attempt < retry:
                time.sleep(15)
    return None

# Сетка bbox-ов, покрывающих Московскую ЖД
# (min_lat, min_lon, max_lat, max_lon)
GRID = [
    (55.5, 36.8, 56.1, 37.7),   # Москва запад
    (55.5, 37.7, 56.1, 38.6),   # Москва восток
    (55.0, 36.5, 55.5, 38.5),   # Юг близко
    (54.5, 36.0, 55.0, 39.0),   # Юг далеко
    (56.1, 36.0, 57.0, 37.5),   # Север запад
    (56.1, 37.5, 57.2, 39.0),   # Север восток
    (55.2, 38.6, 56.2, 40.5),   # Восток ближний
    (55.0, 40.5, 56.0, 42.5),   # Восток дальний
    (55.2, 34.5, 56.2, 36.5),   # Запад ближний
    (55.0, 33.0, 56.0, 34.5),   # Запад дальний
    (54.0, 35.5, 54.5, 40.0),   # Юг дальний
    (56.8, 36.5, 57.5, 40.0),   # Север дальний
]

def fetch_ways(bbox):
    mn_la, mn_lo, mx_la, mx_lo = bbox
    bbox_str = f"{mn_la},{mn_lo},{mx_la},{mx_lo}"
    q = f"""[out:json][timeout:110];
way["railway"="rail"]["usage"~"^(main|branch|regional)$"]({bbox_str});
out geom;"""
    return overpass(q, timeout_http=130)

def simplify(pts, precision=5):
    out, prev = [], None
    for p in pts:
        r = [round(p[0], precision), round(p[1], precision)]
        if r != prev:
            out.append(r)
            prev = r
    return out

def main():
    # ── 1. Станции ──────────────────────────────────────────────────────────
    print("Скачиваем станции/платформы...", end=" ", flush=True)
    q_sta = """[out:json][timeout:180];
(
  node["railway"~"^(station|halt)$"](51.0,33.0,57.5,43.0);
);
out body;"""
    res = overpass(q_sta, timeout_http=200)
    if not res:
        print("ОШИБКА — продолжаем без станций")
        stations = []
    else:
        raw_sta = res["elements"]
        stations = []
        for el in raw_sta:
            tags = el.get("tags", {})
            name = tags.get("name:ru") or tags.get("name") or ""
            if not name:
                continue
            stations.append({
                "lat": round(el["lat"], 5),
                "lon": round(el["lon"], 5),
                "name": name,
                "type": tags.get("railway", "station"),
            })
        print(f"{len(stations)} объектов с именем (из {len(raw_sta)} всего)")

    # ── 2. Пути по сетке ────────────────────────────────────────────────────
    all_ways = {}   # osm_id → [[lat, lon], ...]
    for i, bbox in enumerate(GRID):
        print(f"  Сетка {i+1:2d}/{len(GRID)} {bbox} ...", end=" ", flush=True)
        res = fetch_ways(bbox)
        if not res:
            print("пропускаем")
            continue
        ways = [el for el in res["elements"] if el["type"] == "way" and "geometry" in el]
        added = 0
        for w in ways:
            wid = w["id"]
            if wid not in all_ways:
                pts = simplify([[n["lat"], n["lon"]] for n in w["geometry"]])
                if len(pts) >= 2:
                    all_ways[wid] = pts
                    added += 1
        print(f"+{added} путей (итого {len(all_ways)})")

    # ── 3. Собираем сегменты через null ─────────────────────────────────────
    segments = []
    for pts in all_ways.values():
        if segments:
            segments.append(None)
        segments.extend(pts)
    net_pts = len([p for p in segments if p is not None])

    print(f"\nИтого: {len(stations)} станций, {len(all_ways)} участков, {net_pts} точек")

    # ── 4. Пишем JS ─────────────────────────────────────────────────────────
    out_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mjd_osm_network.js")
    )
    sta_json  = json.dumps(stations, ensure_ascii=False, separators=(",", ":"))
    net_json  = json.dumps(segments, ensure_ascii=False, separators=(",", ":"))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Автогенерация: python3 tools/fetch_mjd_network.py\n")
        f.write(f"const MJD_OSM_STATIONS = {sta_json};\n")
        f.write(f"const MJD_OSM_NETWORK  = {net_json};\n")

    print(f"Сохранено: {out_path}")


if __name__ == "__main__":
    main()
