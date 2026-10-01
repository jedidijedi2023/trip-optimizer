"""Wires the main /api/search route to genuinely connected providers only.

No provider is called here unless it is either (a) an official public demo
that requires no personal registration (Travelgate HOTELTEST), or (b) the
deployment's own environment variables hold credentials the operator
registered for themselves (e.g. RATEHAWK_SANDBOX_KEY_ID/RATEHAWK_SANDBOX_KEY).
This module never falls back to mock/fixture offers — an empty result here
means exactly that: no connected source had anything to say.
"""
import os
from datetime import date, timedelta
from backend.providers.adapters import TravelgateDemo
from backend.providers.base import ProviderUnavailable
from backend.providers.validation_search import ratehawk_search

DEFAULT_REGION_ID = 6053839  # documented RateHawk sandbox region


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


async def gather_live_offers(filters: dict, party: dict, source_settings) -> dict:
    """Returns {'offers': [...], 'attempted': [...]}. Attempted always lists
    every provider this route knows how to call, connected or not, so the
    frontend can show an honest per-provider status regardless of outcome."""
    attempted = []
    offers = []
    if not getattr(source_settings, 'search_wholesalers', True):
        return {'offers': [], 'attempted': [
            {'provider': 'Travelgate HOTELTEST', 'connected': True, 'used': False,
             'count': 0, 'note': 'Отключено переключателем «Искать у оптовиков / B2B»'},
            {'provider': 'RateHawk', 'connected': _bool_ratehawk(), 'used': False,
             'count': 0, 'note': 'Отключено переключателем «Искать у оптовиков / B2B»'},
        ]}

    q = _query(filters, party)

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
        ('Tourvisor', bool(os.getenv('TOURVISOR_TOKEN') and os.getenv('TOURVISOR_ACCESS_MODE') == 'trial'),
         'Токен обнаружен. Нужны справочники departureId/countryId — пока не подключены.'),
    ):
        if env_ready:
            attempted.append({'provider': label, 'connected': True, 'used': False, 'count': 0, 'note': hint})

    return {'offers': offers, 'attempted': attempted}


def _bool_ratehawk() -> bool:
    return bool(os.getenv('RATEHAWK_SANDBOX_KEY_ID') and os.getenv('RATEHAWK_SANDBOX_KEY'))
