"""Wires the main /api/search route to genuinely connected providers only.

No provider is called here unless it is either (a) an official public demo
that requires no personal registration (Travelgate HOTELTEST), (b) a free,
instant-token official data API (Travelpayouts / Aviasales Data API), or
(c) a sandbox whose own credentials the operator has put in backend/.env
(e.g. RATEHAWK_SANDBOX_KEY_ID/RATEHAWK_SANDBOX_KEY). This module never falls
back to mock/fixture offers — an empty result here means exactly that: no
connected source had anything to say.
"""
import os
from datetime import date, timedelta
from backend.providers.adapters import TravelgateDemo
from backend.providers.base import ProviderUnavailable
from backend.providers.validation_search import ratehawk_search
from backend.providers.travelpayouts import AviasalesFlightData, travelpayouts_token

DEFAULT_REGION_ID = 6053839  # documented RateHawk sandbox region

# Only destinations represented by the search form are eligible for retail
# flight suggestions. Cached flight prices are never expanded into a family
# total or combined with demo hotel prices.
BEACH_AIRPORTS = {
    'EG': {'HRG', 'SSH'}, 'TR': {'AYT', 'DLM', 'BJV', 'IST'},
    'TH': {'HKT', 'BKK', 'KBV', 'USM'}, 'MV': {'MLE'},
    'OM': {'SLL', 'MCT'}, 'AE': {'DXB', 'AUH', 'RKT', 'SHJ'},
    'VN': {'PQC', 'CXR', 'DAD', 'SGN'}, 'LK': {'CMB'},
    'ID': {'DPS'}, 'SC': {'SEZ'}, 'MU': {'MRU'},
    'TZ': {'ZNZ'}, 'MY': {'LGK', 'KUL'}, 'PH': {'MPH', 'KLO', 'MNL'},
    'IN': {'GOI', 'GOX'}, 'QA': {'DOH'}, 'ES': {'PMI'},
}
COUNTRY_NAMES = {
    'EG': 'египет', 'TR': 'турция', 'TH': 'таиланд', 'MV': 'мальдивы',
    'OM': 'оман', 'AE': 'оаэ', 'VN': 'вьетнам', 'LK': 'шри-ланка',
    'ID': 'индонезия', 'SC': 'сейшелы', 'MU': 'маврикий',
    'TZ': 'танзания', 'MY': 'малайзия', 'PH': 'филиппины',
    'IN': 'индия', 'QA': 'катар', 'ES': 'испания',
}
PRIMARY_BEACH_AIRPORTS = {
    'EG': 'SSH', 'TR': 'AYT', 'TH': 'HKT', 'AE': 'DXB', 'MV': 'MLE',
    'OM': 'SLL', 'VN': 'PQC', 'LK': 'CMB', 'ID': 'DPS', 'SC': 'SEZ',
    'MU': 'MRU', 'TZ': 'ZNZ', 'MY': 'LGK', 'PH': 'MPH', 'IN': 'GOI',
    'QA': 'DOH', 'ES': 'PMI',
}


def _query(filters: dict, party: dict) -> dict:
    try:
        check_in = date.fromisoformat(str(filters.get('earliest')))
    except (TypeError, ValueError):
        check_in = date.today() + timedelta(days=30)
    try:
        nights = max(1, min(28, int(filters.get('minNights', 7))))
    except (TypeError, ValueError):
        nights = 7
    check_out = check_in + timedelta(days=nights)
    adults = int(party.get('adults', 2)) if isinstance(party, dict) else 2
    children = party.get('children', []) if isinstance(party, dict) else []
    children = [int(a) for a in children if isinstance(a, (int, float))][:4]
    nationality = str(filters.get('citizenship', 'RU'))[:2].upper() or 'RU'
    return {
        'check_in': str(check_in), 'check_out': str(check_out),
        'adults': max(1, min(8, adults)), 'children': children,
        'nationality': nationality, 'region_id': DEFAULT_REGION_ID,
    }


def _first_airport(filters: dict) -> str | None:
    raw = filters.get('airports') or filters.get('departureAirports')
    if not raw:
        return None
    first = str(raw).split(',')[0].strip().upper()
    return first if 2 <= len(first) <= 4 else None


def _flight_window(filters: dict):
    today = date.today() + timedelta(days=1)
    try:
        start = max(today, date.fromisoformat(str(filters['earliest'])))
        last_departure = date.fromisoformat(str(filters['latestDeparture']))
        last_return = date.fromisoformat(str(filters['latest']))
        min_nights = max(1, int(filters.get('minNights', 1)))
        max_nights = max(min_nights, int(filters.get('maxNights', 60)))
    except (KeyError, TypeError, ValueError):
        return None
    if start > last_departure:
        return None
    return start, last_departure, last_return, min_nights, max_nights


def _selected_countries(filters: dict) -> set[str]:
    if filters.get('destinationMode') != 'Выбранные страны':
        return set(BEACH_AIRPORTS)
    tokens = {value.strip().casefold() for value in str(filters.get('destinations', '')).replace(';', ',').split(',')}
    return {code for code, name in COUNTRY_NAMES.items()
            if code.casefold() in tokens or name in tokens or (code == 'TH' and 'тайланд' in tokens)}


def _months(start: date, end: date) -> list[str]:
    months = []
    current = start.replace(day=1)
    while current <= end and len(months) < 3:
        months.append(current.strftime('%Y-%m'))
        current = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
    return months


async def _travelpayouts_offers(origin: str, filters: dict):
    window = _flight_window(filters)
    if not window:
        return [], 'Нет будущих дат вылета в выбранном окне'
    start, last_departure, last_return, min_nights, max_nights = window
    countries = _selected_countries(filters)
    if not countries:
        return [], 'Не выбрана ни одна поддерживаемая страна'
    airport_country = {airport: code for code in countries for airport in BEACH_AIRPORTS[code]}
    by_id = {}
    months = _months(start, last_departure)
    provider = AviasalesFlightData()

    async def collect(month: str, destination: str | None = None):
        rows = await provider.prices_for_dates(origin, destination=destination,
                                               departure_at=month, sorting='price',
                                               unique=False, limit=1000 if destination is None else 300)
        for offer in rows:
            code = airport_country.get(offer.destination or '')
            if not code or not offer.departure_date or not offer.return_date:
                continue
            nights = (offer.return_date - offer.departure_date).days
            if not (start <= offer.departure_date <= last_departure
                    and offer.return_date <= last_return and min_nights <= nights <= max_nights):
                continue
            offer.country_code = code
            previous = by_id.get(offer.id)
            if previous is None or offer.price.original_amount < previous.price.original_amount:
                by_id[offer.id] = offer

    for month in months:
        await collect(month)
    # An origin-wide page is capped at 1000 and sorted by price. Long-haul
    # beaches may fall off that page, so retry a small set of documented IATA
    # destinations when it yielded no matching route.
    if not by_id:
        if filters.get('destinationMode') == 'Выбранные страны':
            destinations = [PRIMARY_BEACH_AIRPORTS[code] for code in sorted(countries)]
            if len(countries) == 1:
                code = next(iter(countries))
                destinations += sorted(BEACH_AIRPORTS[code] - {PRIMARY_BEACH_AIRPORTS[code]})
        else:
            destinations = [PRIMARY_BEACH_AIRPORTS[code] for code in ('EG', 'TR', 'TH', 'AE', 'MV')]
        for destination in destinations[:5]:
            for month in months:
                await collect(month, destination)
    return sorted(by_id.values(), key=lambda offer: offer.price.original_amount)[:30], None


async def gather_live_offers(filters: dict, party: dict, source_settings) -> dict:
    """Returns {'offers': [...], 'attempted': [...]}. Attempted always lists
    every provider this route knows how to call, connected or not, so the
    frontend can show an honest per-provider status regardless of outcome."""
    attempted = []
    offers = []
    operators_on = getattr(source_settings, 'search_tour_operators', True)
    russian_operators_on = getattr(source_settings, 'search_russian_operators', True)
    foreign_operators_on = getattr(source_settings, 'search_foreign_operators', True)
    wholesalers_on = getattr(source_settings, 'search_wholesalers', True)
    retail_on = getattr(source_settings, 'search_retail_diy', True)
    q = _query(filters, party)

    if operators_on and (russian_operators_on or foreign_operators_on):
        tourvisor_ready = bool(os.getenv('TOURVISOR_TOKEN') and os.getenv('TOURVISOR_ACCESS_MODE') == 'trial')
        attempted.append({'provider': 'Tourvisor', 'connected': tourvisor_ready, 'used': False,
                          'count': 0, 'note': 'Токен есть, но общий поиск пока не задаёт ID справочников страны и вылета' if tourvisor_ready else 'Для тарифов на выбранную семью нужен собственный официальный trial-токен Tourvisor'})
        attempted.append({'provider': 'Travelata partner API', 'connected': False, 'used': False,
                          'count': 0, 'note': 'Токен Aviasales не открывает API Travelata. Партнёрские логин и пароль выдаются Travelata индивидуально; опубликованные цены без точного состава семьи показаны отдельно выше'})

    if not wholesalers_on:
        attempted.append({'provider': 'Travelgate HOTELTEST', 'connected': True, 'used': False,
                           'count': 0, 'note': 'Отключено переключателем «Искать у оптовиков / B2B»'})
        attempted.append({'provider': 'RateHawk', 'connected': _bool_ratehawk(), 'used': False,
                           'count': 0, 'note': 'Отключено переключателем «Искать у оптовиков / B2B»'})
    else:
        # Travelgate HOTELTEST — official public demo, no personal key needed.
        try:
            tg_offers = await TravelgateDemo().search(q)
            offers += tg_offers
            attempted.append({'provider': 'Travelgate HOTELTEST', 'connected': True, 'used': True,
                               'count': len(tg_offers), 'note': None})
        except Exception as exc:
            attempted.append({'provider': 'Travelgate HOTELTEST', 'connected': True, 'used': True,
                               'count': 0, 'note': 'UPSTREAM_UNAVAILABLE: ' + type(exc).__name__})

        # RateHawk sandbox — only if the operator's own sandbox keys are set.
        if _bool_ratehawk():
            try:
                rh_offers = await ratehawk_search(q)
                offers += rh_offers
                attempted.append({'provider': 'RateHawk', 'connected': True, 'used': True,
                                   'count': len(rh_offers), 'note': None})
            except ProviderUnavailable as exc:
                attempted.append({'provider': 'RateHawk', 'connected': True, 'used': True,
                                   'count': 0, 'note': str(exc)})
            except Exception as exc:
                attempted.append({'provider': 'RateHawk', 'connected': True, 'used': True,
                                   'count': 0, 'note': 'UPSTREAM_UNAVAILABLE: ' + type(exc).__name__})
        else:
            attempted.append({'provider': 'RateHawk', 'connected': False, 'used': False, 'count': 0,
                               'note': 'Нужны RATEHAWK_SANDBOX_KEY_ID и RATEHAWK_SANDBOX_KEY в backend/.env'})

    if not retail_on:
        attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': _bool_travelpayouts(),
                           'used': False, 'count': 0,
                           'note': 'Отключено переключателем «Самостоятельная розничная сборка»'})
    elif _bool_travelpayouts():
        origin = _first_airport(filters)
        if not origin:
            attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': True, 'used': False,
                               'count': 0, 'note': 'Укажите хотя бы один аэропорт вылета в фильтрах'})
        else:
            try:
                fl_offers, note = await _travelpayouts_offers(origin, filters)
                offers += fl_offers
                attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': True, 'used': True,
                                   'count': len(fl_offers), 'note': note or ('В полученной части кэша нет билетов для выбранных стран, дат и длительности' if not fl_offers else 'Кэшированная цена билета; не тариф для всей семьи')})
            except ProviderUnavailable as exc:
                attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': True, 'used': True,
                                   'count': 0, 'note': str(exc)})
            except Exception as exc:
                attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': True, 'used': True,
                                   'count': 0, 'note': 'UPSTREAM_UNAVAILABLE: ' + type(exc).__name__})
    else:
        attempted.append({'provider': 'Travelpayouts / Aviasales Data API', 'connected': False, 'used': False,
                           'count': 0, 'note': 'Нужен личный TRAVELPAYOUTS_TOKEN в Environment сервиса Render; доступ к API зависит от статуса аккаунта'})

    # Providers whose sandbox call needs inputs the general search form does not
    # collect (specific hotel codes, a fixed flight route, dictionary IDs).
    # Reported honestly as connected-but-not-wired rather than guessed at.
    for label, env_ready, hint in (
        ('Duffel', bool((os.getenv('DUFFEL_TOKEN') or '').startswith('duffel_test_')),
         'Ключ обнаружен. Общая форма поиска не задаёт конкретный маршрут A→B — протестируйте во вкладке «API тест», где есть поля вылета/прилёта.'),
        ('Hotelbeds / HBX', bool(os.getenv('HOTELBEDS_API_KEY') and os.getenv('HOTELBEDS_SECRET')),
         'Ключи обнаружены. Нужны конкретные коды отелей — протестируйте во вкладке «API тест».'),
        ('DidaTravel rates', bool(os.getenv('DIDA_CLIENT_ID') and os.getenv('DIDA_LICENSE_KEY') and os.getenv('DIDA_ENVIRONMENT') == 'sandbox'),
         'Учётные данные обнаружены. Нормализация тарифов ждёт подтверждённого ответа поставщика.'),
    ):
        if env_ready:
            attempted.append({'provider': label, 'connected': True, 'used': False, 'count': 0, 'note': hint})

    return {'offers': offers, 'attempted': attempted}


def _bool_ratehawk() -> bool:
    return bool(os.getenv('RATEHAWK_SANDBOX_KEY_ID') and os.getenv('RATEHAWK_SANDBOX_KEY'))


def _bool_travelpayouts() -> bool:
    return bool(travelpayouts_token())
