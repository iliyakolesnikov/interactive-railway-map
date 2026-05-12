#!/usr/bin/env python3
"""
МЖД Flask API — сервер для управления станциями и остановками.

Зависимости:
    pip install flask flask-cors psycopg2-binary

PostgreSQL (создать базу и пользователя):
    sudo -u postgres psql
    CREATE DATABASE mjd;
    -- или использовать существующего пользователя postgres

Переменные окружения (или задать DB_* ниже):
    DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_PORT

Запуск:
    python3 server.py
    Карта:    http://localhost:8080/
    Админка:  http://localhost:8080/admin.html
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
import sys

app = Flask(__name__, static_folder='.')
CORS(app)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_NAME = os.getenv('DB_NAME', 'mjd')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_PORT = int(os.getenv('DB_PORT', '5432'))

# Начальные данные — Савёловское направление
INITIAL_STATIONS = [
    {"name": "Москва-Бутырская (Савёловский вокзал)", "lat": 55.795758, "lon": 37.588529, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Тимирязевская",                          "lat": 55.819336, "lon": 37.575509, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Окружная",                               "lat": 55.847650, "lon": 37.574156, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Дегунино",                               "lat": 55.865540, "lon": 37.573221, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Бескудниково",                           "lat": 55.882192, "lon": 37.567543, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Лианозово",                              "lat": 55.898881, "lon": 37.548868, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Марк",                                   "lat": 55.904391, "lon": 37.538297, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Новодачная",                             "lat": 55.924339, "lon": 37.527707, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Долгопрудная",                           "lat": 55.939983, "lon": 37.520025, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Водники",                                "lat": 55.952556, "lon": 37.512443, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Хлебниково",                             "lat": 55.952556, "lon": 37.512443, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Шереметьевская",                         "lat": 55.952556, "lon": 37.512443, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Аэропорт Шереметьево Север",             "lat": 55.983294, "lon": 37.413610, "type": "Остановка",  "line": "Ветка на аэропорт"},
    {"name": "Аэропорт Шереметьево Юг",                "lat": 55.963854, "lon": 37.415829, "type": "Остановка",  "line": "Ветка на аэропорт"},
    {"name": "Лобня",                                  "lat": 56.013212, "lon": 37.484646, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Депо",                                   "lat": 56.027817, "lon": 37.486102, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Луговая",                                "lat": 56.027817, "lon": 37.486102, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Некрасовская",                           "lat": 56.074418, "lon": 37.495879, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Катуар",                                 "lat": 56.090854, "lon": 37.504245, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Трудовая",                               "lat": 56.120792, "lon": 37.515042, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Икша",                                   "lat": 56.120792, "lon": 37.515042, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Морозки",                                "lat": 56.120792, "lon": 37.515042, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Турист",                                 "lat": 56.243443, "lon": 37.512105, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Яхрома",                                 "lat": 56.286491, "lon": 37.501815, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Дмитров",                                "lat": 56.337579, "lon": 37.510237, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Каналстрой",                             "lat": 56.383303, "lon": 37.515701, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "75 км (им.Барсученко)",                  "lat": 56.418938, "lon": 37.497390, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Орудьево",                               "lat": 56.445821, "lon": 37.519955, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Вербилки",                               "lat": 56.538995, "lon": 37.559976, "type": "Станция",    "line": "Савеловское направление"},
    {"name": "Соревнование",                           "lat": 56.529056, "lon": 37.430049, "type": "Станция",    "line": "Ветка на Дубну"},
    {"name": "Запрудня",                               "lat": 56.560633, "lon": 37.393002, "type": "Остановка",  "line": "Ветка на Дубну"},
    {"name": "Темпы",                                  "lat": 56.635402, "lon": 37.296682, "type": "Остановка",  "line": "Ветка на Дубну"},
    {"name": "Мельдино",                               "lat": 56.658677, "lon": 37.261749, "type": "Остановка",  "line": "Ветка на Дубну"},
    {"name": "119 км",                                 "lat": 56.678479, "lon": 37.226737, "type": "Остановка",  "line": "Ветка на Дубну"},
    {"name": "Карманово (122 км)",                     "lat": 56.691793, "lon": 37.192219, "type": "Остановка",  "line": "Ветка на Дубну"},
    {"name": "Большая Волга",                          "lat": 56.726833, "lon": 37.136656, "type": "Станция",    "line": "Ветка на Дубну"},
    {"name": "Дубна",                                  "lat": 56.745962, "lon": 37.201221, "type": "Станция",    "line": "Ветка на Дубну"},
    {"name": "94 км (Никулки)",                        "lat": 56.580448, "lon": 37.567980, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Власово",                                "lat": 56.645558, "lon": 37.563482, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Талдом",                                 "lat": 56.722456, "lon": 37.525980, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Лебзино",                                "lat": 56.769690, "lon": 37.419653, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "124 км",                                 "lat": 56.809934, "lon": 37.382958, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Савёлово",                               "lat": 56.855938, "lon": 37.377624, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Белый городок",                          "lat": 56.949232, "lon": 37.538110, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "151 км",                                 "lat": 56.999880, "lon": 37.566002, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Стрельчиха",                             "lat": 57.024767, "lon": 37.589876, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "163 км",                                 "lat": 57.089071, "lon": 37.667803, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Скнятино",                               "lat": 57.101095, "lon": 37.687807, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Новокатово",                             "lat": 57.178169, "lon": 37.746007, "type": "Остановка",  "line": "Савеловское направление"},
    {"name": "Эра (177 км)",                           "lat": 57.203912, "lon": 37.769694, "type": "Остановка",  "line": "Савеловское направление"},
]


def get_db():
    return psycopg2.connect(
        host=DB_HOST, dbname=DB_NAME, user=DB_USER,
        password=DB_PASS, port=DB_PORT
    )


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS stations (
            id         SERIAL PRIMARY KEY,
            name       VARCHAR(255) NOT NULL,
            lat        NUMERIC(10,7) NOT NULL,
            lon        NUMERIC(10,7) NOT NULL,
            type       VARCHAR(50) NOT NULL DEFAULT 'Остановка',
            line       VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("SELECT COUNT(*) FROM stations")
    if cur.fetchone()[0] == 0:
        for s in INITIAL_STATIONS:
            cur.execute(
                "INSERT INTO stations (name, lat, lon, type, line) VALUES (%s,%s,%s,%s,%s)",
                (s["name"], s["lat"], s["lon"], s["type"], s.get("line"))
            )
        print(f"Заполнена начальная БД: {len(INITIAL_STATIONS)} объектов")
    conn.commit()
    conn.close()


# ── API ────────────────────────────────────────────────────────────────────

@app.route("/api/stations", methods=["GET"])
def api_get_stations():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id, name, lat::float, lon::float, type, line FROM stations ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/stations", methods=["POST"])
def api_add_station():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Поле 'name' обязательно"}), 400
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Некорректные координаты"}), 400
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"error": "Координаты вне допустимого диапазона"}), 400
    type_ = data.get("type", "Остановка")
    if type_ not in ("Станция", "Остановка"):
        return jsonify({"error": "type должен быть 'Станция' или 'Остановка'"}), 400
    line = (data.get("line") or "").strip() or None

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO stations (name, lat, lon, type, line) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (name, lat, lon, type_, line)
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"id": new_id, "name": name, "lat": lat, "lon": lon, "type": type_, "line": line}), 201


@app.route("/api/stations/<int:sid>", methods=["PUT"])
def api_update_station(sid):
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Поле 'name' обязательно"}), 400
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Некорректные координаты"}), 400
    type_ = data.get("type", "Остановка")
    line = (data.get("line") or "").strip() or None

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE stations SET name=%s, lat=%s, lon=%s, type=%s, line=%s WHERE id=%s",
        (name, lat, lon, type_, line, sid)
    )
    conn.commit()
    conn.close()
    return jsonify({"id": sid, "name": name, "lat": lat, "lon": lon, "type": type_, "line": line})


@app.route("/api/stations/<int:sid>", methods=["DELETE"])
def api_delete_station(sid):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM stations WHERE id=%s", (sid,))
    conn.commit()
    conn.close()
    return "", 204


# ── Статические файлы ──────────────────────────────────────────────────────

@app.route("/")
def serve_index():
    return send_from_directory(".", "index_2.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(".", path)


# ── Запуск ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Подключение к PostgreSQL...")
    try:
        init_db()
    except psycopg2.OperationalError as e:
        print(f"\nОшибка подключения к БД:\n  {e}")
        print("\nПроверьте настройки DB_HOST/DB_NAME/DB_USER/DB_PASS/DB_PORT")
        print("или создайте БД командой:")
        print("  sudo -u postgres psql -c \"CREATE DATABASE mjd;\"")
        sys.exit(1)
    print("БД готова. Сервер: http://localhost:8080")
    print("Карта:    http://localhost:8080/")
    print("Админка:  http://localhost:8080/admin.html")
    app.run(host="0.0.0.0", port=8080, debug=False)
