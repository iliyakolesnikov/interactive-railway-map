#!/usr/bin/env python3
"""
Докачивает пропущенный участок Казанского направления:
  Амерево → Карасево и Амерево → Рязань-1
  (bbox 54.5–55.2 lat, 38.5–40.5 lon — не покрыт основной сеткой)

Результат: дополняет mjd_osm_network.js без повторного скачивания всего.

Запускать из Project_v41/:
    python3 tools/patch_kazan_east.py
"""
import json, re, urllib.request, urllib.parse, sys, os, time

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Пропущенная зона: восток Казанского направления
PATCH_CELLS = [
    (54.5, 38.5, 55.2, 40.5),   # Амерево–Карасево–Рязань-1
]


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


def simplify(pts, precision=5):
    out, prev = [], None
    for p in pts:
        r = [round(p[0], precision), round(p[1], precision)]
        if r != prev:
            out.append(r)
            prev = r
    return out


def fetch_ways(bbox):
    mn_la, mn_lo, mx_la, mx_lo = bbox
    bbox_str = f"{mn_la},{mn_lo},{mx_la},{mx_lo}"
    q = f"""[out:json][timeout:110];
way["railway"~"^(rail|narrow_gauge)$"]["service"!~"^(crossover|siding|yard)$"]["tunnel"!="yes"]({bbox_str});
out geom;"""
    return overpass(q, timeout_http=130)


def main():
    out_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mjd_osm_network.js")
    )

    # ── 1. Читаем текущие данные ─────────────────────────────────────────────
    print(f"Читаем {out_path} ...", end=" ", flush=True)
    with open(out_path, encoding="utf-8") as f:
        src = f.read()

    # Извлекаем существующие сегменты (MJD_OSM_NETWORK)
    net_match = re.search(r"const MJD_OSM_NETWORK\s*=\s*(\[.*?\]);", src, re.DOTALL)
    sta_match = re.search(r"const MJD_OSM_STATIONS\s*=\s*(\[.*?\]);", src, re.DOTALL)
    if not net_match or not sta_match:
        print("ОШИБКА: не найдены переменные в mjd_osm_network.js")
        sys.exit(1)

    existing_segments = json.loads(net_match.group(1))
    existing_stations = json.loads(sta_match.group(1))

    # Собираем существующие ID через хеш координат первой точки каждого way
    # (у нас нет OSM ID в JS, дедупликация по набору координат)
    existing_coords: set = set()
    current_way: list = []
    for pt in existing_segments:
        if pt is None:
            if current_way:
                existing_coords.add(tuple(current_way[0]))
            current_way = []
        else:
            if not current_way:
                current_way = []
            current_way.append(tuple(pt))
    if current_way:
        existing_coords.add(tuple(current_way[0]))

    print(f"загружено {len(existing_coords)} участков")

    # ── 2. Скачиваем пропущенную зону ────────────────────────────────────────
    new_ways: dict = {}   # osm_id → [[lat, lon], ...]
    for i, bbox in enumerate(PATCH_CELLS):
        print(f"  Ячейка {i+1}/{len(PATCH_CELLS)} {bbox} ...", end=" ", flush=True)
        res = fetch_ways(bbox)
        if not res:
            print("пропускаем")
            continue
        ways = [el for el in res["elements"] if el["type"] == "way" and "geometry" in el]
        added = 0
        for w in ways:
            pts = simplify([[n["lat"], n["lon"]] for n in w["geometry"]])
            if len(pts) < 2:
                continue
            if tuple(pts[0]) not in existing_coords:
                new_ways[w["id"]] = pts
                added += 1
        print(f"+{added} новых участков")

    if not new_ways:
        print("Нет новых участков — файл не изменён.")
        return

    # ── 3. Скачиваем новые станции в зоне ────────────────────────────────────
    print("Скачиваем станции пропущенной зоны ...", end=" ", flush=True)
    q_sta = """[out:json][timeout:60];
(
  node["railway"~"^(station|halt)$"]["station"!="subway"]["station"!="monorail"](54.5,38.5,55.2,40.5);
);
out body;"""
    res_sta = overpass(q_sta, timeout_http=80)
    new_stations = []
    if res_sta:
        METRO_KW = ("метрополитен", "metro", "метро", "монорельс", "monorail", "мцк", "mcc")
        existing_sta_keys = {(s["lat"], s["lon"]) for s in existing_stations}
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
                new_stations.append({
                    "lat": key[0], "lon": key[1],
                    "name": name,
                    "type": tags.get("railway", "station"),
                })
        print(f"+{len(new_stations)} новых станций")
    else:
        print("ошибка — станции не добавлены")

    # ── 4. Объединяем и пишем ────────────────────────────────────────────────
    all_stations = existing_stations + new_stations

    patch_segments = []
    for pts in new_ways.values():
        if patch_segments:
            patch_segments.append(None)
        patch_segments.extend(pts)

    all_segments = existing_segments + [None] + patch_segments if patch_segments else existing_segments

    sta_json = json.dumps(all_stations, ensure_ascii=False, separators=(",", ":"))
    net_json = json.dumps(all_segments, ensure_ascii=False, separators=(",", ":"))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("// Автогенерация: python3 tools/fetch_mjd_network.py\n")
        f.write(f"const MJD_OSM_STATIONS = {sta_json};\n")
        f.write(f"const MJD_OSM_NETWORK  = {net_json};\n")

    total_ways = len(existing_coords) + len(new_ways)
    print(f"\nГотово: +{len(new_ways)} участков, +{len(new_stations)} станций → {out_path}")
    print(f"Итого участков в файле: {total_ways}")


if __name__ == "__main__":
    main()
