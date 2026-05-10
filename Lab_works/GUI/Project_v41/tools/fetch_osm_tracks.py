#!/usr/bin/env python3
"""
Скачивает геометрию маршрутов МЦД и основных путей МЖД из Overpass API.
Результат записывается в mjd_tracks_data.js.

Запускать из папки Project_v41/:
    python3 tools/fetch_osm_tracks.py
"""
import json, urllib.request, urllib.parse, sys, os, math

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Relation IDs МЦД в OSM (один маршрут на каждый диаметр — полный пробег)
MCD_RELATIONS = {
    "d1": {"id": 10309185, "color": "#f7b500",
           "name": "МЦД-1 · Одинцово — Лобня"},
    "d2": {"id": 10309306, "color": "#e91e8c",
           "name": "МЦД-2 · Нахабино — Подольск"},
    "d3": {"id": 16213700, "color": "#4caf50",
           "name": "МЦД-3 · Крюково — Раменское"},
    "d4": {"id": 16272078, "color": "#9c27b0",
           "name": "МЦД-4 · Апрелевка — Железнодорожная"},
}


def overpass(query, timeout_http=180):
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
          headers={"User-Agent": "MJD-map-project/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_http) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  ошибка запроса: {e}", file=sys.stderr)
        return None


def dist2(a, b):
    return (a[0]-b[0])**2 + (a[1]-b[1])**2


def build_path(ways):
    """Соединяет фрагменты пути (ways) в упорядоченную полилинию."""
    if not ways:
        return []
    segments = []
    for w in ways:
        geom = w.get("geometry", [])
        if len(geom) >= 2:
            segments.append([[n["lat"], n["lon"]] for n in geom])
    if not segments:
        return []

    path = list(segments[0])
    remaining = segments[1:]

    while remaining:
        tail = path[-1]
        best_i, best_rev, best_d = 0, False, float("inf")
        for i, seg in enumerate(remaining):
            df = dist2(tail, seg[0])
            dr = dist2(tail, seg[-1])
            if df < best_d:
                best_d, best_i, best_rev = df, i, False
            if dr < best_d:
                best_d, best_i, best_rev = dr, i, True
        seg = remaining.pop(best_i)
        if best_rev:
            seg = seg[::-1]
        # Не дублировать стыковой узел
        start = 1 if (dist2(path[-1], seg[0]) < 1e-10) else 0
        path.extend(seg[start:])

    return path


def simplify(coords, precision=4):
    """Округляет координаты и убирает дубликаты соседних точек."""
    out = []
    prev = None
    for pt in coords:
        p = [round(pt[0], precision), round(pt[1], precision)]
        if p != prev:
            out.append(p)
            prev = p
    return out


def fetch_relation(rel_id):
    """Скачивает геометрию одного relation по ID."""
    q = f"""[out:json][timeout:90];
relation({rel_id});
>>;
out geom;"""
    print(f"  Запрос relation/{rel_id}…", end=" ", flush=True)
    res = overpass(q, timeout_http=120)
    if not res:
        return []
    ways = [el for el in res["elements"] if el["type"] == "way" and "geometry" in el]
    path = build_path(ways)
    path = simplify(path, precision=4)
    print(f"{len(path)} точек из {len(ways)} сегментов")
    return path


def fetch_rail_network():
    """Скачивает основные жд пути в Московском регионе."""
    # bbox покрывает МЖД в радиусе ~200 км от Москвы
    q = """[out:json][timeout:120];
(
  way["railway"="rail"]["usage"="main"](54.8,35.5,56.8,40.5);
);
out geom;"""
    print("Запрос основной сети МЖД (usage=main)…", end=" ", flush=True)
    res = overpass(q, timeout_http=150)
    if not res:
        print("не удалось загрузить")
        return []
    ways = [el for el in res["elements"] if el["type"] == "way" and "geometry" in el]
    print(f"получено {len(ways)} участков")
    # Каждый way → отдельный сегмент, разделённые null
    segments = []
    for w in ways:
        pts = simplify([[n["lat"], n["lon"]] for n in w.get("geometry", [])], precision=4)
        if len(pts) >= 2:
            if segments:
                segments.append(None)   # разрыв между сегментами
            segments.extend(pts)
    print(f"  Итого точек в сети: {len([p for p in segments if p is not None])}")
    return segments


def main():
    mcd_data = {}
    for key, meta in MCD_RELATIONS.items():
        print(f"МЦД {key.upper()} ({meta['name']}):")
        coords = fetch_relation(meta["id"])
        if not coords:
            print(f"  ⚠ Не удалось загрузить {key}, пропускаем")
            continue
        mcd_data[key] = {
            "color":  meta["color"],
            "name":   meta["name"],
            "coords": coords,
        }

    print("\nОсновная сеть МЖД:")
    rail_net = fetch_rail_network()

    # Формируем JS-файл
    js_lines = ["// Автогенерация: python3 tools/fetch_osm_tracks.py",
                "// МЦД и основная сеть МЖД из OpenStreetMap.",
                ""]

    # МЦД
    js_lines.append("const MJD_MCD = {")
    for key, meta in mcd_data.items():
        coords_json = json.dumps(meta["coords"], ensure_ascii=False, separators=(",", ":"))
        js_lines.append(f'  {key}: {{')
        js_lines.append(f'    color: "{meta["color"]}",')
        js_lines.append(f'    name: "{meta["name"]}",')
        js_lines.append(f'    coords: {coords_json}')
        js_lines.append(f'  }},')
    js_lines.append("};")
    js_lines.append("")

    # Основная сеть (сегменты через null)
    net_json = json.dumps(rail_net, ensure_ascii=False, separators=(",", ":"))
    js_lines.append(f"const MJD_RAIL_NET = {net_json};")

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mjd_tracks_data.js")
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(js_lines) + "\n")

    total_mcd_pts = sum(len(v["coords"]) for v in mcd_data.values())
    net_pts = len([p for p in rail_net if p is not None])
    print(f"\nГотово: {out_path}")
    print(f"  МЦД: {len(mcd_data)} маршрутов, {total_mcd_pts} точек")
    print(f"  Сеть: {net_pts} точек в {len([p for p in rail_net if p is None])+1} сегментах")


if __name__ == "__main__":
    main()
