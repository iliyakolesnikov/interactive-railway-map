#!/usr/bin/env python3
"""
Находит все станции без путей и докачивает недостающие bbox-ячейки из Overpass.
Запускать из Project_v41/:
    python3 tools/patch_missing_coverage.py
"""
import json, re, math, time, urllib.request, urllib.parse, sys, os
from collections import defaultdict

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ORPHAN_THRESHOLD_KM = 0.5   # станция «сирота», если дальше 500 м от любого пути
MIN_ORPHANS_PER_CELL = 3    # пропускаем ячейки с менее чем N сиротами
CELL_DEG = 2.0              # размер генерируемых ячеек (градусы)

# ── утилиты ──────────────────────────────────────────────────────────────────

def overpass(query, timeout_http=150, retry=3):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
          headers={"User-Agent": "MJD-map-project/1.0"})
    for attempt in range(retry + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout_http) as resp:
                return json.loads(resp.read())
        except Exception as e:
            print(f"    попытка {attempt+1} ошибка: {e}", file=sys.stderr)
            if attempt < retry:
                wait = 20 * (attempt + 1)
                print(f"    ждём {wait}с...", file=sys.stderr)
                time.sleep(wait)
    return None

def simplify(pts, precision=5):
    out, prev = [], None
    for p in pts:
        r = [round(p[0], precision), round(p[1], precision)]
        if r != prev:
            out.append(r)
            prev = r
    return out

def build_path_grid(network):
    """Сетка 0.05° для быстрого поиска ближайшего пути."""
    g = defaultdict(list)
    for pt in network:
        if pt:
            g[(round(pt[0] * 20) / 20, round(pt[1] * 20) / 20)].append(pt)
    return g

def min_dist_km(lat, lon, path_grid):
    best = 9999.0
    for dlat in (-0.05, 0.0, 0.05):
        for dlon in (-0.05, 0.0, 0.05):
            cell = (round((lat + dlat) * 20) / 20, round((lon + dlon) * 20) / 20)
            for pt in path_grid[cell]:
                d = math.sqrt((pt[0] - lat) ** 2 * 12100 + (pt[1] - lon) ** 2 * 8100)
                if d < best:
                    best = d
    return best

def collect_existing_starts(network):
    """Хэш-набор первых точек каждого way для дедупликации."""
    seen, cur = set(), []
    for pt in network:
        if pt is None:
            if cur:
                seen.add(tuple(cur[0]))
            cur = []
        else:
            cur.append(tuple(pt))
    if cur:
        seen.add(tuple(cur[0]))
    return seen

# ── основная логика ───────────────────────────────────────────────────────────

def fetch_ways(bbox):
    mn_la, mn_lo, mx_la, mx_lo = bbox
    q = f"""[out:json][timeout:120];
way["railway"~"^(rail|narrow_gauge)$"]["service"!~"^(crossover|siding|yard)$"]["tunnel"!="yes"]({mn_la},{mn_lo},{mx_la},{mx_lo});
out geom;"""
    return overpass(q, timeout_http=140)

def fetch_stations(bbox):
    mn_la, mn_lo, mx_la, mx_lo = bbox
    q = f"""[out:json][timeout:60];
(node["railway"~"^(station|halt)$"]["station"!="subway"]["station"!="monorail"]({mn_la},{mn_lo},{mx_la},{mx_lo}););
out body;"""
    return overpass(q, timeout_http=80)

METRO_KW = ("метрополитен", "metro", "метро", "монорельс", "monorail", "мцк", "mcc")

def main():
    out_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mjd_osm_network.js")
    )

    # ── 1. Загружаем текущее состояние ───────────────────────────────────────
    print("Читаем mjd_osm_network.js ...", end=" ", flush=True)
    with open(out_path, encoding="utf-8") as f:
        src = f.read()
    network  = json.loads(re.search(r"const MJD_OSM_NETWORK\s*=\s*(\[.*?\]);",  src, re.DOTALL).group(1))
    stations = json.loads(re.search(r"const MJD_OSM_STATIONS\s*=\s*(\[.*?\]);", src, re.DOTALL).group(1))
    print(f"{len(stations)} станций, {sum(1 for p in network if p is None)+1} участков")

    path_grid     = build_path_grid(network)
    existing_starts = collect_existing_starts(network)

    # ── 2. Находим сироты ────────────────────────────────────────────────────
    print("Ищем станции без путей ...", end=" ", flush=True)
    orphans = [s for s in stations
               if min_dist_km(s["lat"], s["lon"], path_grid) > ORPHAN_THRESHOLD_KM]
    print(f"{len(orphans)} сирот из {len(stations)}")

    if not orphans:
        print("Все станции на путях — ничего делать не нужно.")
        return

    # ── 3. Кластеризуем по ячейкам CELL_DEG×CELL_DEG ────────────────────────
    clusters = defaultdict(list)
    for s in orphans:
        cell = (
            math.floor(s["lat"] / CELL_DEG) * CELL_DEG,
            math.floor(s["lon"] / CELL_DEG) * CELL_DEG,
        )
        clusters[cell].append(s)

    needed = sorted(
        [(cell, pts) for cell, pts in clusters.items() if len(pts) >= MIN_ORPHANS_PER_CELL],
        key=lambda x: -len(x[1])
    )
    print(f"\nНужно докачать {len(needed)} ячеек (≥{MIN_ORPHANS_PER_CELL} сирот):\n")
    for (clat, clon), pts in needed:
        print(f"  [{clat:.1f}–{clat+CELL_DEG:.1f}°N, {clon:.1f}–{clon+CELL_DEG:.1f}°E]  {len(pts)} сирот")

    # ── 4. Качаем ячейки по очереди ──────────────────────────────────────────
    total_new_ways = 0
    total_new_sta  = 0
    all_new_segments: list = []
    all_new_stations: list = []
    existing_sta_keys = {(s["lat"], s["lon"]) for s in stations}

    for i, ((clat, clon), orphan_pts) in enumerate(needed):
        bbox = (clat, clon, clat + CELL_DEG, clon + CELL_DEG)
        print(f"\n[{i+1}/{len(needed)}] bbox {bbox}  ({len(orphan_pts)} сирот)  ...", flush=True)

        # Пути
        res = fetch_ways(bbox)
        if not res:
            print("  ОШИБКА — пропускаем")
            continue
        new_ways = {}
        for w in res["elements"]:
            if w["type"] != "way" or "geometry" not in w:
                continue
            pts = simplify([[n["lat"], n["lon"]] for n in w["geometry"]])
            if len(pts) >= 2 and tuple(pts[0]) not in existing_starts:
                new_ways[w["id"]] = pts
                existing_starts.add(tuple(pts[0]))
        print(f"  +{len(new_ways)} новых участков путей")
        total_new_ways += len(new_ways)

        for pts in new_ways.values():
            if all_new_segments:
                all_new_segments.append(None)
            all_new_segments.extend(pts)

        # Обновляем path_grid новыми путями, чтобы следующие ячейки не дублировались
        for pts in new_ways.values():
            for pt in pts:
                path_grid[(round(pt[0] * 20) / 20, round(pt[1] * 20) / 20)].append(pt)

        # Станции
        res_sta = fetch_stations(bbox)
        if res_sta:
            for el in res_sta["elements"]:
                tags = el.get("tags", {})
                name = tags.get("name:ru") or tags.get("name") or ""
                if not name:
                    continue
                net = (tags.get("network", "") + tags.get("network:ru", "")).lower()
                op  = tags.get("operator", "").lower()
                if any(kw in net or kw in op for kw in METRO_KW):
                    continue
                key = (round(el["lat"], 5), round(el["lon"], 5))
                if key not in existing_sta_keys:
                    all_new_stations.append({
                        "lat": key[0], "lon": key[1],
                        "name": name,
                        "type": tags.get("railway", "station"),
                    })
                    existing_sta_keys.add(key)
            print(f"  +{len([s for s in all_new_stations])} новых станций (накоп.)")
            total_new_sta = len(all_new_stations)

        # Небольшая пауза, чтобы не перегружать Overpass
        if i < len(needed) - 1:
            time.sleep(5)

    if not all_new_segments:
        print("\nНе добавлено ни одного нового пути.")
        return

    # ── 5. Пишем объединённый файл ───────────────────────────────────────────
    all_stations_out = stations + all_new_stations
    all_network_out  = network + [None] + all_new_segments

    sta_json = json.dumps(all_stations_out, ensure_ascii=False, separators=(",", ":"))
    net_json = json.dumps(all_network_out,  ensure_ascii=False, separators=(",", ":"))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Автогенерация: python3 tools/fetch_mjd_network.py\n")
        f.write(f"const MJD_OSM_STATIONS = {sta_json};\n")
        f.write(f"const MJD_OSM_NETWORK  = {net_json};\n")

    print(f"\n{'='*60}")
    print(f"Готово! +{total_new_ways} участков путей, +{total_new_sta} станций")
    print(f"Файл: {out_path}")

    # ── 6. Проверка ──────────────────────────────────────────────────────────
    new_grid = build_path_grid(all_network_out)
    still_orphans = [s for s in all_stations_out
                     if min_dist_km(s["lat"], s["lon"], new_grid) > ORPHAN_THRESHOLD_KM]
    print(f"Осталось сирот: {len(still_orphans)} (было {len(orphans)})")
    if still_orphans[:10]:
        print("Первые 10:")
        for s in still_orphans[:10]:
            d = min_dist_km(s["lat"], s["lon"], new_grid)
            print(f"  {d:.1f} км  {s['name']}  lat={s['lat']} lon={s['lon']}")

if __name__ == "__main__":
    main()
