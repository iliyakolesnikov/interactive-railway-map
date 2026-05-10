#!/usr/bin/env python3
"""
Скачивает станции/остановки МЖД из Overpass API и сохраняет в osm_lookup.json.
Запускать из папки Project_v41/:
    python3 tools/fetch_osm_railway.py
Результат: osm_lookup.json (в .gitignore — не коммитить).
"""
import json, urllib.request, urllib.parse, time, sys, os

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# bbox охватывает всю сеть МЖД (Москва + ~600 км)
BBOX = "50.0,30.0,57.5,42.5"

QUERY = f"""
[out:json][timeout:180];
(
  node["railway"~"^(station|halt|stop)$"]({BBOX});
  node["railway"="level_crossing"]({BBOX});
  node["railway"="signal_box"]({BBOX});
  node["power"="substation"]["substation"="traction"]({BBOX});
);
out body;
"""

def normalize(name):
    return str(name).lower().replace("ё", "е").strip()

def fetch():
    print("Отправка запроса к Overpass API (может занять 1–2 мин)…")
    data = urllib.parse.urlencode({"data": QUERY}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data,
          headers={"User-Agent": "MJD-map-project/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=200) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"Ошибка запроса: {e}", file=sys.stderr)
        sys.exit(1)
    return json.loads(raw)

def main():
    result = fetch()
    elements = result.get("elements", [])
    print(f"Получено элементов: {len(elements)}")

    lookup = {}      # нормализованное_имя → данные
    by_type = {}     # railway-тип → кол-во

    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            continue

        name_ru = tags.get("name:ru") or tags.get("name") or ""
        name_en = tags.get("name:en") or ""
        railway  = tags.get("railway", "")
        power    = tags.get("power", "")
        subst    = tags.get("substation", "")

        # Определяем категорию
        if power == "substation" and subst == "traction":
            category = "traction_substation"
        elif railway == "signal_box":
            category = "signal_box"
        elif railway == "level_crossing":
            category = "crossing"
        else:
            category = railway  # station / halt / stop

        by_type[category] = by_type.get(category, 0) + 1

        if not name_ru:
            continue  # без имени — бесполезно для матчинга

        # Данные для обогащения объекта
        entry = {
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "osm_id": el.get("id"),
            "category": category,
            "name": name_ru,
            "name_en": name_en,
            "electrified": tags.get("electrified", ""),
            "voltage": tags.get("voltage", ""),
            "frequency": tags.get("frequency", ""),
            "tracks": tags.get("tracks", ""),
            "operator": tags.get("operator", ""),
            "network": tags.get("network", ""),
            "ref": tags.get("ref", ""),
            "addr_city": tags.get("addr:city", ""),
            "addr_street": tags.get("addr:street", ""),
            "start_date": tags.get("start_date", ""),
            "wheelchair": tags.get("wheelchair", ""),
        }

        key = normalize(name_ru)
        # Если дубликат — оставить с более полными данными (больше непустых полей)
        if key in lookup:
            old = lookup[key]
            filled_new = sum(1 for v in entry.values() if v)
            filled_old = sum(1 for v in old.values() if v)
            if filled_new <= filled_old:
                continue

        lookup[key] = entry

    # Сохраняем
    out_path = os.path.join(os.path.dirname(__file__), "..", "osm_lookup.json")
    out_path = os.path.normpath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)

    print(f"\nСтатистика по категориям:")
    for k, v in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    print(f"\nОбъектов с именем (записано в lookup): {len(lookup)}")
    print(f"Сохранено: {out_path}")

if __name__ == "__main__":
    main()
