#!/usr/bin/env python3
"""Generate INFRA arrays — real OSM coords where available, interpolation as fallback."""
import json, os

def chain_stops(waypoints, stops):
    """waypoints: [(lat,lng), ...]; stops: [(name, kind), ...]"""
    if not stops or len(waypoints) < 2:
        return []
    total_len = 0.0
    for i in range(len(waypoints) - 1):
        a, b = waypoints[i], waypoints[i + 1]
        total_len += ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    n = len(stops)
    out = []
    for idx, (name, kind) in enumerate(stops):
        t = (idx + 1) / (n + 1)
        dist = t * total_len
        acc = 0.0
        for i in range(len(waypoints) - 1):
            a, b = waypoints[i], waypoints[i + 1]
            seg = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
            if acc + seg >= dist - 1e-12:
                frac = (dist - acc) / seg if seg > 0 else 0.0
                lat = a[0] + (b[0] - a[0]) * frac
                lng = a[1] + (b[1] - a[1]) * frac
                out.append((name, kind, lat, lng))
                break
            acc += seg
        else:
            out.append((name, kind, waypoints[-1][0], waypoints[-1][1]))
    return out

# Moscow anchors
Moscow_KUR = (55.7558, 37.6592)
Moscow_GOR = (55.7558, 37.6592)
Moscow_YAR = (55.7763, 37.6561)
Moscow_KAZ = (55.7732, 37.6559)
Moscow_PAV = (55.7297, 37.6474)
Moscow_KIE = (55.7438, 37.5656)
Moscow_SML = (55.7769, 37.5817)
Moscow_RIG = (55.7931, 37.6344)
Moscow_SAV = (55.7936, 37.5900)

Podolsk = (55.4310, 37.5450)
Serpukhov = (54.9158, 37.4117)
Tarus = (54.7650, 37.1750)
Leonovo = (55.5980, 37.9080)
Orekhovo = (55.8058, 38.9610)
Alexandrov = (56.3980, 38.7050)
Cherusti = (55.2170, 39.7660)
Kurovskaya = (55.5770, 38.9060)
Ryazanovka = (55.6050, 39.0880)
Domodedovo = (55.4360, 37.7670)
Zhilyovo = (54.9510, 38.2340)
Smolensk = (54.7820, 32.0450)
Shakhovskaya = (55.8940, 35.5050)
Dubna = (56.7310, 37.1700)
Apar = (55.5480, 37.0810)
Bekasovo = (55.4050, 37.0680)
Stolbovaya = (55.2510, 37.4820)
Tula = (54.1931, 37.6172)
Orel = (52.9703, 36.0633)
Kursk = (51.7373, 36.1873)
Gagarin = (55.5528, 35.0496)
Golutvin = (55.0930, 38.7680)
Ozery = (54.8570, 38.5450)
Berebino = (55.0760, 38.9060)
Lopatino = (55.0720, 38.8260)
Egorevsk = (55.3830, 38.9520)

# Москва — Подольск и южнее (две цепочки — корректнее по положению на карте)
KUR_A = [
    ("Каланчёвская", "halt"),
    ("Серп и Молот", "halt"),
    ("Карачарово", "halt"),
    ("Перово", "node"),
    ("Люблино", "pass"),
    ("Депо (о.п.)", "halt"),
    ("Царицыно", "halt"),
    ("Покровская", "halt"),
    ("Коломенская", "halt"),
    ("Остапово", "halt"),
    ("Бирюлёво-Пассажирское", "halt"),
    ("Булатниково", "halt"),
    ("Битца", "halt"),
    ("Щербинка", "halt"),
    ("Силикатная", "halt"),
]
KUR_B = [
    ("Подольск (платф.)", "halt"),
    ("Кутузово", "halt"),
    ("Гривно", "halt"),
    ("Весенняя", "halt"),
    ("Чехов", "halt"),
    ("Чехов 2", "halt"),
    ("Ока", "halt"),
    ("Тарусская", "halt"),
]

GOR_STOPS = [
    ("Электрозаводская", "halt"),
    ("Новая", "halt"),
    ("Чухлинка", "halt"),
    ("Вешняки", "halt"),
    ("Выхино", "halt"),
    ("Косино", "halt"),
    ("Красково", "halt"),
    ("Малаховка", "halt"),
    ("Быково", "halt"),
    ("Фрязево", "halt"),
    ("Электроугли", "halt"),
    ("Захарово", "halt"),
    ("Купавна", "halt"),
    ("88 км", "halt"),
    ("Храпуново", "halt"),
    ("Дрезна", "halt"),
    ("Покров", "halt"),
    ("Леоново", "halt"),
]

YAR_STOPS = [
    ("Маленковская", "halt"),
    ("Северянин", "halt"),
    ("Перловская", "halt"),
    ("Тайнинская", "halt"),
    ("Болшево", "halt"),
    ("Клязьма", "halt"),
    ("Мамонтовская", "halt"),
    ("Заветы Ильича", "halt"),
    ("Правда", "halt"),
    ("Зеленоградская", "halt"),
    ("Радонеж", "halt"),
    ("Абрамцево", "halt"),
    ("Семхоз", "halt"),
    ("Деревенька", "halt"),
    ("Арсаки", "halt"),
    ("Ельдигино", "halt"),
    ("Аксаково", "halt"),
]

KAZ_STOPS = [
    ("Серп и Молот (Казанский ход)", "halt"),
    ("Люберцы-2", "halt"),
    ("Панки", "halt"),
    ("Томилино", "halt"),
    ("Красково", "halt"),
    ("Малаховка", "halt"),
    ("Быково", "halt"),
    ("Фабричная", "halt"),
    ("Бронницы", "halt"),
    ("Голутвин-участок", "halt"),
    ("Пески", "halt"),
    ("Хорлово", "halt"),
    ("Белые Столбы", "halt"),
    ("Хутор", "halt"),
    ("Запутная", "halt"),
    ("Давыдово", "halt"),
    ("Мишеронский", "halt"),
    ("Бакшеево", "halt"),
]

KAZ_BRANCH = [
    ("Запутная", "halt"),
    ("Кривандино", "pass"),
    ("Рязановка", "pass"),
]

PAV_STOPS = [
    ("Павелецкая (платф.)", "halt"),
    ("Нижние Котлы", "halt"),
    ("Коломенское", "halt"),
    ("Депо (павелецкий ход)", "halt"),
    ("Царицыно (павел. ход)", "halt"),
    ("Бирюлёво-Пасс.", "halt"),
    ("Взлётная", "halt"),
    ("Растуново", "halt"),
    ("Барыбино", "halt"),
    ("Михнево", "halt"),
    ("Усадово", "halt"),
    ("Ситенка", "halt"),
]

SML_STOPS = [
    ("Беговая", "halt"),
    ("Фили", "halt"),
    ("Кунцево-1", "halt"),
    ("Кунцево-2", "halt"),
    ("Баковка", "halt"),
    ("Перхушково", "halt"),
    ("Жаворонки", "halt"),
    ("Хлюпино", "halt"),
    ("Тучково", "halt"),
    ("Дорохово", "halt"),
    ("Уваровка", "halt"),
    ("Шаликово", "halt"),
    ("Колочь", "halt"),
    ("Часцы", "halt"),
]

RIG_STOPS = [
    ("Покровское-Стрешнево", "halt"),
    ("Красный Балтиец", "halt"),
    ("Лихоборы", "halt"),
    ("Ховрино", "halt"),
    ("Новоподрезково", "halt"),
    ("Подрезково", "halt"),
    ("Аникеевка", "halt"),
    ("Румянцево", "halt"),
    ("Снегири", "halt"),
    ("Холщёво", "halt"),
    ("Опалиха", "halt"),
    ("Павловская Слобода", "halt"),
    ("Чисмена", "halt"),
    ("Буйгород", "halt"),
]

SAV_STOPS = [
    ("Тимирязевская", "halt"),
    ("Окружная", "halt"),
    ("Лихоборы", "halt"),
    ("Красный Строитель", "halt"),
    ("Новодачная", "halt"),
    ("Водники", "halt"),
    ("Луговая", "halt"),
    ("Катуар", "halt"),
    ("Турист", "halt"),
    ("Орево", "halt"),
    ("Яхрома", "halt"),
    ("Соревнование", "halt"),
    ("Темпы", "halt"),
    ("Вербилки", "halt"),
]

KIE_STOPS = [
    ("Алабино", "halt"),
    ("Кокошкино", "halt"),
]

BIC_w = [
    ("Бекасово-Центральное", "halt"),
]

TUL_STOPS = [
    ("Подсерёдка", "halt"),
    ("Алексин", "halt"),
]

ORL_STOPS = [
    ("Скуратово", "halt"),
    ("Плавск", "halt"),
    ("Горбачёво", "halt"),
    ("Мценск", "halt"),
    ("Малоархангельск", "halt"),
    ("Золотухино", "halt"),
    ("Охочевка", "halt"),
]

SMO_STOPS = [
    ("Пилево", "halt"),
    ("Касня", "halt"),
    ("Дорогобуж", "halt"),
    ("Издешково", "halt"),
]

OZ_STOPS = [
    ("Щурово", "halt"),
    ("Дивово", "halt"),
]

BIG_STOPS = [
    ("Ратмирово", "halt"),
]

PASS_EXTRA = [
    ("Москва-Каланчёвская", Moscow_KUR[0], Moscow_KUR[1], "pass"),
    ("Фрязево (станция)", 55.7330, 38.0450, "pass"),
    ("Крутое", 55.7680, 38.1020, "pass"),
    ("Коломна", 55.0930, 38.7530, "pass"),
    ("Воскресенск", 55.3210, 38.6510, "pass"),
    ("Фруктовая", 54.9890, 39.0550, "pass"),
    ("Куровская", Kurovskaya[0], Kurovskaya[1], "pass"),
    ("Шатура", 55.5760, 39.5380, "pass"),
    ("Черусти", Cherusti[0], Cherusti[1], "pass"),
    ("Кашира", 54.8310, 38.1620, "pass"),
    ("Узуново", 54.9830, 40.1740, "pass"),
    ("Непецино", 55.1190, 39.0180, "pass"),
    ("Берендино", Berebino[0], Berebino[1], "pass"),
    ("Лопатино", Lopatino[0], Lopatino[1], "pass"),
    ("Егорьевск-2", 55.3230, 39.0350, "pass"),
    ("Звенигород", 55.7290, 36.8550, "pass"),
    ("Кубинка-1", 55.5790, 36.6930, "pass"),
    ("Бекасово-1", Bekasovo[0], Bekasovo[1], "pass"),
    ("Столбовая", Stolbovaya[0], Stolbovaya[1], "pass"),
    ("Осёнка", 55.2180, 38.8120, "pass"),
    ("Монино", 55.8420, 38.1950, "pass"),
    ("Наугольная", 56.0580, 37.2950, "pass"),
    ("Поварово-3", 56.0930, 37.2680, "pass"),
    ("Софрино", 56.1510, 38.2800, "pass"),
    ("Озёры", Ozery[0], Ozery[1], "pass"),
    ("Зарайск", 54.7620, 38.8850, "pass"),
    ("Ряжск-2", 53.7080, 40.0680, "pass"),
    ("Коренево", 51.4150, 34.9950, "pass"),
    ("Суджа", 51.1920, 35.2710, "pass"),
    ("Готня", 50.9730, 35.7750, "pass"),
    ("Карачев", 53.1290, 34.9880, "pass"),
    ("Калуга-2", 54.5130, 36.2610, "pass"),
    ("Новомосковск-2", 54.0380, 38.2950, "pass"),
    ("Рязань-1", 54.6269, 39.6916, "pass"),
    ("Рязань-2", 54.6150, 39.7050, "pass"),
    ("Ряжск", 53.7080, 40.0680, "pass"),
    ("Павелец-Тульский", 53.0400, 41.0460, "pass"),
    ("Скопин", 54.0040, 41.9510, "pass"),
    ("Михайлов", 54.2310, 39.0550, "pass"),
    ("Луховицы", 54.9650, 39.0260, "pass"),
    ("Жилёво", Zhilyovo[0], Zhilyovo[1], "pass"),
    ("Ожерелье", 54.8050, 38.2740, "pass"),
    ("Венёв", 54.3510, 38.2680, "pass"),
    ("Тула-1 (Тула-Курская)", Tula[0], Tula[1], "pass"),
    ("Тула-2 (Тула-Рязанская)", 54.1880, 37.6450, "pass"),
    ("Узловая", 53.9740, 38.1650, "pass"),
    ("Новомосковск-1", 54.0340, 38.2980, "pass"),
    ("Плавск", 53.7080, 37.2910, "pass"),
    ("Ефремов", 53.1460, 38.1190, "pass"),
    ("Змиёвка", 52.6450, 36.3780, "pass"),
    ("Поныри", 52.1150, 36.2520, "pass"),
    ("Льгов-2", 51.7090, 35.2680, "pass"),
    ("Белгород", 50.5950, 36.5850, "pass"),
    ("Сафоново", 55.1050, 33.2400, "pass"),
    ("Ярцево", 55.0660, 32.6960, "pass"),
    ("Дорогобуж", 54.9130, 33.3080, "pass"),
    ("Красное", 55.0660, 30.1010, "pass"),
    ("Брянск-2 (Брянск-Льговский)", 53.2434, 34.3654, "pass"),
    ("Сельцо", 53.3730, 34.1000, "pass"),
    ("Навля", 52.8240, 34.4970, "pass"),
    ("Суземка", 52.7180, 34.0780, "pass"),
    ("Унеча", 52.8450, 32.6740, "pass"),
    ("Клинцы", 52.7580, 32.2340, "pass"),
    ("Новозыбков", 52.5360, 31.9350, "pass"),
    ("Злынка", 52.4260, 31.7360, "pass"),
    ("Стародуб", 52.5850, 32.7620, "pass"),
    ("Дубровка", 53.6910, 33.3100, "pass"),
    ("Рославль-1", 53.9510, 32.8560, "pass"),
    ("Сухиничи-Узловые", 54.0830, 35.3480, "pass"),
    ("Занозная", 55.4110, 34.9840, "pass"),
    ("Людиново-1", 53.8680, 34.4470, "pass"),
    ("Думиничи", 53.9230, 35.1120, "pass"),
]

NODES = [
    ("Железнодорожная", 55.3510, 38.0190),
    ("Орехово-Зуево", Orekhovo[0], Orekhovo[1]),
    ("Голутвин", Golutvin[0], Golutvin[1]),
    ("Орёл", Orel[0], Orel[1]),
    ("Курск", Kursk[0], Kursk[1]),
    ("Льгов-1", 51.7090, 35.2680),
    ("Сухиничи-Главные", 54.0830, 35.3480),
    ("Фаянсовая", 58.5960, 49.6680),
    ("Вязьма", 55.2110, 34.2980),
    ("Смоленск", Smolensk[0], Smolensk[1]),
    ("Егорьевск-1", Egorevsk[0], Egorevsk[1]),
    ("Серпухов", Serpukhov[0], Serpukhov[1]),
    ("Горбачёво", 53.2740, 36.4830),
    ("Калуга-1", 54.5130, 36.2610),
    ("Дмитров", 56.3440, 37.5200),
    ("Истра", 55.9210, 36.8680),
    ("Волоколамск", 56.0120, 35.9680),
    ("Можайск", 55.5060, 36.0190),
    ("Бородино", 55.6400, 35.8280),
    ("Гагарин", Gagarin[0], Gagarin[1]),
    ("Пушкино", 55.9910, 37.8310),
    ("Александров-1", Alexandrov[0], Alexandrov[1]),
    ("Раменское", 55.5660, 38.2280),
    ("Домодедово", Domodedovo[0], Domodedovo[1]),
    ("Ступино", 54.9010, 38.0780),
    ("Хотьково", 56.2520, 37.9810),
    ("Сергиев Посад", 56.3000, 38.1340),
    ("Удельная", 55.6320, 38.0480),
    ("Голутвин (Коломна)", Golutvin[0], Golutvin[1]),
    ("Воскресенск", 55.3210, 38.6510),
]

SORT_EXTRA = [
    ("Лосиноостровская", 55.8700, 37.6880),
    ("Рыбное", 54.7380, 39.5110),
    ("Бекасово-Сортировочное", 55.3930, 37.0040),
    ("Москва-Сортировочная-Киевская", 55.7300, 37.5350),
    ("Ховрино (сорт.)", 55.8780, 37.5080),
]

FR_EXTRA = [
    ("Москва-Товарная-Курская", 55.7380, 37.6780),
    ("Москва-Южный Порт", 55.6830, 37.6880),
    ("Москва-Рижская (грузовая)", 55.7910, 37.6320),
    ("Москва-Бутырская", 55.7970, 37.5950),
    ("Москва-Каланчёвская (груз.)", 55.7760, 37.6470),
    ("Курск-товарная", Kursk[0], Kursk[1]),
    ("Орёл-товарный", Orel[0], Orel[1]),
    ("Смоленск-товарный", Smolensk[0], Smolensk[1]),
    ("Мценск", 53.3120, 36.5740),
    ("Мытищи (груз.)", 55.9100, 37.7320),
    ("Фрязево (груз.)", 55.7330, 38.0450),
    ("Подольск (груз.)", Podolsk[0], Podolsk[1]),
    ("Нара", 55.3850, 36.7350),
]

DEP_EXTRA = [
    ("Депо Москва-2 (Ярославская)", 55.8230, 37.7380),
    ("Депо Перерва", 55.6620, 37.7380),
    ("Депо Домодедово", Domodedovo[0], Domodedovo[1]),
    ("Депо Куровская", Kurovskaya[0], Kurovskaya[1]),
    ("Депо Подмосковная", 55.8130, 37.5170),
    ("Депо им. Ильича", 55.7350, 37.4450),
    ("Депо Лихоборы (ист.)", 55.8470, 37.5540),
    ("Депо Александров", Alexandrov[0], Alexandrov[1]),
    ("Депо Рязань", 54.6269, 39.6916),
    ("Депо Орёл", Orel[0], Orel[1]),
    ("ТЧЭ Бекасово", 55.4020, 37.0600),
    ("ТЧЭ Узуново", 54.9830, 40.1740),
    ("ТЧЭ Орехово", Orekhovo[0], Orekhovo[1]),
    ("ТЧЭ Голутвин", Golutvin[0], Golutvin[1]),
    ("ТЧЭ Тула", Tula[0], Tula[1]),
    ("ТЧЭ Курск", Kursk[0], Kursk[1]),
    ("ТЧЭ Орёл", Orel[0], Orel[1]),
    ("ТЧЭ Вязьма", 55.2110, 34.2980),
    ("ТЧЭ Брянск", 53.2434, 34.3654),
    ("ТЧЭ Ожерелье", 54.8050, 38.2740),
    ("ТЧР Москва-3", 55.7600, 37.7400),
    ("ТЧР Рыбное", 54.7380, 39.5110),
    ("ТЧР Бекасово", 55.4020, 37.0600),
    ("ТЧР Орехово-Зуево", Orekhovo[0], Orekhovo[1]),
]

DEPOT_VAG = [
    ("Вагонное депо Москва-Сортировочная", 55.7600, 37.7400),
    ("Вагонное депо Перово", 55.7520, 37.7990),
    ("Вагонное депо Подольск", Podolsk[0], Podolsk[1]),
    ("Вагонное депо Люблино", 55.6840, 37.8940),
    ("Вагонное депо Орёл", Orel[0], Orel[1]),
    ("Вагонное депо Рязань", 54.6269, 39.6916),
    ("Вагонное депо Курск", Kursk[0], Kursk[1]),
    ("Вагонное депо Брянск", 53.2434, 34.3654),
    ("Вагонное депо Смоленск", Smolensk[0], Smolensk[1]),
]

def load_osm_lookup():
    """Загружает osm_lookup.json если он существует."""
    import os
    path = os.path.join(os.path.dirname(__file__), "osm_lookup.json")
    if not os.path.exists(path):
        print("osm_lookup.json не найден — используем только интерполяцию.")
        print("Запустите: python3 tools/fetch_osm_railway.py")
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Загружено {len(data)} OSM-записей из osm_lookup.json")
    return data

def make_desc(kind, osm):
    """Формирует осмысленное описание объекта."""
    line = osm.get("network", "").replace("Московская железная дорога", "МЖД").strip()
    start = osm.get("start_date", "")
    if kind == "halt":
        base = f"Остановочный пункт{(' ' + line) if line else ''}."
        if start:
            base += f" Открыт: {start}."
        return base
    if kind == "pass":
        return f"Пассажирская станция{(' ' + line) if line else ''}."
    if kind == "node":
        return f"Узловая станция МЖД."
    return "Объект инфраструктуры МЖД."

def make_stats(kind, osm):
    """Формирует stats из OSM-тегов."""
    stats = {}
    electrified = osm.get("electrified", "")
    voltage = osm.get("voltage", "")
    frequency = osm.get("frequency", "")
    tracks = osm.get("tracks", "")
    operator = osm.get("operator", "")
    network = osm.get("network", "")
    ref = osm.get("ref", "")
    wheelchair = osm.get("wheelchair", "")
    addr_city = osm.get("addr_city", "")
    addr_street = osm.get("addr_street", "")

    # Электрификация
    if electrified and electrified not in ("no", ""):
        if voltage == "3000":
            elec_str = "3 кВ DC"
        elif voltage == "25000":
            elec_str = "25 кВ AC"
        elif voltage:
            freq_part = f" {frequency} Гц" if frequency else ""
            elec_str = f"{int(voltage)//1000} кВ{freq_part}"
        else:
            elec_str = "есть"
        stats["Электрификация"] = elec_str
    elif electrified == "no":
        stats["Электрификация"] = "нет (тепловозная тяга)"

    if tracks:
        stats["Кол-во путей"] = tracks
    if ref:
        stats["Код ЕСР"] = ref
    if wheelchair == "yes":
        stats["Доступность"] = "для МГН"
    if network:
        net = network.replace("Московская железная дорога", "МЖД")
        if net and kind in ("pass", "halt", "node"):
            stats["Сеть"] = net
    if operator and operator != "ОАО «РЖД»":
        stats["Оператор"] = operator
    addr = " ".join(filter(None, [addr_city, addr_street]))
    if addr:
        stats["Адрес"] = addr
    if kind in ("pass", "halt"):
        stats["Статус"] = "РАБОТАЕТ"
    return stats

def main():
    osm = load_osm_lookup()

    out_pass = []
    out_halt = []
    out_node = []
    seen = set()
    pid = [0]
    osm_hits = [0]
    osm_misses = [0]

    def add(name, lat, lng, kind):
        k = name.lower().replace("ё", "е").strip()
        if k in seen:
            return
        seen.add(k)
        pid[0] += 1
        oid = f"inf{pid[0]}"

        # Пробуем взять точные координаты из OSM
        osm_rec = osm.get(k, {})
        if osm_rec:
            use_lat = osm_rec["lat"]
            use_lng = osm_rec["lon"]
            snap = False
            osm_hits[0] += 1
        else:
            use_lat = round(lat, 4)
            use_lng = round(lng, 4)
            snap = True
            osm_misses[0] += 1

        rec = {
            "id": oid,
            "type": kind,
            "name": name,
            "lat": round(use_lat, 6),
            "lng": round(use_lng, 6),
            "snap": snap,
            "desc": make_desc(kind, osm_rec),
            "stats": make_stats(kind, osm_rec),
        }
        if kind == "pass":
            out_pass.append(rec)
        elif kind == "halt":
            out_halt.append(rec)
        elif kind == "node":
            out_node.append(rec)

    for row in chain_stops([Moscow_KUR, Podolsk], KUR_A):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Podolsk, Serpukhov, Tarus], KUR_B):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_GOR, Orekhovo, Leonovo], GOR_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_YAR, Alexandrov], YAR_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_KAZ, Kurovskaya, Cherusti], KAZ_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Kurovskaya, Ryazanovka], KAZ_BRANCH):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_PAV, Domodedovo, Zhilyovo], PAV_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_SML, Smolensk], SML_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_RIG, Shakhovskaya], RIG_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_SAV, Dubna], SAV_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Moscow_KIE, Apar], KIE_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Bekasovo, Stolbovaya], BIC_w):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Serpukhov, Tula], TUL_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Tula, Orel, Kursk], ORL_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Gagarin, Smolensk], SMO_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Golutvin, Ozery], OZ_STOPS):
        add(row[0], row[2], row[3], row[1])

    for row in chain_stops([Berebino, Lopatino], BIG_STOPS):
        add(row[0], row[2], row[3], row[1])

    for name, lat, lng, kind in PASS_EXTRA:
        add(name, lat, lng, kind)

    for name, lat, lng in NODES:
        add(name, lat, lng, "node")

    out_sort = []
    out_fr = []
    out_dep = []
    out_dv = []

    def add_extra(name, lat, lng, kind):
        k = name.lower().replace("ё", "е").strip()
        if k in seen:
            return
        seen.add(k)
        pid[0] += 1
        oid = f"inf{pid[0]}"
        osm_rec = osm.get(k, {})
        if osm_rec:
            use_lat = osm_rec["lat"]
            use_lng = osm_rec["lon"]
            snap = False
        else:
            use_lat = round(lat, 4)
            use_lng = round(lng, 4)
            snap = True
        rec = {
            "id": oid,
            "type": kind,
            "name": name,
            "lat": round(use_lat, 6),
            "lng": round(use_lng, 6),
            "snap": snap,
            "desc": "Объект инфраструктуры МЖД.",
            "stats": make_stats(kind, osm_rec),
        }
        if kind == "sorting":
            out_sort.append(rec)
        elif kind == "freight":
            out_fr.append(rec)
        elif kind == "depot":
            out_dep.append(rec)
        elif kind == "depot_vag":
            out_dv.append(rec)

    for name, lat, lng in SORT_EXTRA:
        add_extra(name, lat, lng, "sorting")

    for name, lat, lng in FR_EXTRA:
        add_extra(name, lat, lng, "freight")

    for name, lat, lng in DEP_EXTRA:
        add_extra(name, lat, lng, "depot")

    for name, lat, lng in DEPOT_VAG:
        add_extra(name, lat, lng, "depot_vag")

    total = len(out_pass)+len(out_halt)+len(out_node)+len(out_sort)+len(out_fr)+len(out_dep)+len(out_dv)
    pct = round(osm_hits[0] / max(1, osm_hits[0]+osm_misses[0]) * 100)
    print(f"// PASS {len(out_pass)} HALT {len(out_halt)} NODE {len(out_node)} SORT {len(out_sort)} FR {len(out_fr)} DEP {len(out_dep)} DV {len(out_dv)}")
    print(f"// Всего: {total} | OSM-координаты: {osm_hits[0]} ({pct}%) | интерполяция: {osm_misses[0]}")

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_generated_infra.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "pass": out_pass,
                "halt": out_halt,
                "node": out_node,
                "sorting": out_sort,
                "freight": out_fr,
                "depot": out_dep,
                "depot_vag": out_dv,
            },
            f,
            ensure_ascii=False,
        )
    print(f"Сохранено: {out_path}")

if __name__ == "__main__":
    main()
