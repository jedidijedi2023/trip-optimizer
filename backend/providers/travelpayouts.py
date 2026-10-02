"""Travelpayouts / Aviasales Data API — official, free-to-register partner API.

Docs: https://support.travelpayouts.com/hc/en-us/articles/203956163
Sign-up: https://www.travelpayouts.com/ (token from the operator's own account;
account activation is subject to Travelpayouts requirements — unlike the Hotellook live Hotel *Search* API and
the Kiwitaxi transfer program, both of which require an individual approval
request; see backend/providers/registry.py for the honest status of those).

Only ever called with TRAVELPAYOUTS_TOKEN read from this deployment's own
environment or Render secret file — never a shared or found token.
"""
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from backend.providers.http import http
from backend.providers.base import ProviderUnavailable
from backend.models.domain import NormalizedOffer, Provenance, Money, Access, Reality

SOURCE_URL = 'https://support.travelpayouts.com/hc/en-us/articles/203956163'
SECRET_PATH = Path('/etc/secrets/TRAVELPAYOUTS_TOKEN')


def travelpayouts_token() -> str | None:
    """Read the operator's credential without exposing it to the frontend."""
    token = (os.getenv('TRAVELPAYOUTS_TOKEN') or '').strip()
    if not token:
        try:
            token = SECRET_PATH.read_text(encoding='utf-8').strip()
        except OSError:
            return None
    if token.startswith('TRAVELPAYOUTS_TOKEN='):
        token = token.partition('=')[2].strip().strip('"\'')
    return token or None


class AviasalesFlightData:
    """Cached cheapest fares Aviasales users actually found in the last 48h.
    Real prices from a real, official data feed — but a cache snapshot, not a
    live fare confirmation, so it is never bookable and never Reality.REAL."""

    async def prices_for_dates(self, origin: str, destination: str | None = None, departure_at: str | None = None,
                                currency: str = 'rub', limit: int = 10, sorting: str = 'price',
                                unique: bool = False) -> list[NormalizedOffer]:
        token = travelpayouts_token()
        if not token:
            raise ProviderUnavailable('TRAVELPAYOUTS_TOKEN is not configured')
        params = {'origin': origin, 'currency': currency, 'limit': limit,
                  'sorting': sorting, 'unique': str(unique).lower(), 'one_way': 'false'}
        if destination:
            params['destination'] = destination
        if departure_at:
            params['departure_at'] = departure_at
        result = await http.request('travelpayouts_aviasales', 'GET',
                                     'https://api.travelpayouts.com/aviasales/v3/prices_for_dates',
                                     params=params, headers={'X-Access-Token': token}, ttl=1800)
        body = result['response']
        if not isinstance(body, dict) or not body.get('success'):
            raise ProviderUnavailable(f'Aviasales Data API error: {body.get("error") if isinstance(body, dict) else "invalid response"}')
        offers = []
        for row in body.get('data', []):
            if not isinstance(row, dict):
                continue
            try:
                outbound = date.fromisoformat(str(row.get('departure_at', ''))[:10])
                inbound = date.fromisoformat(str(row.get('return_at', ''))[:10])
                amount = Decimal(str(row['price']))
                if amount <= 0 or inbound <= outbound:
                    continue
            except (KeyError, TypeError, ValueError, ArithmeticError):
                continue
            link = row.get('link')
            search_url = ('https://www.aviasales.ru' + link) if isinstance(link, str) and link.startswith('/search/') and not link.startswith('//') else None
            fetched = datetime.now(timezone.utc)
            offers.append(NormalizedOffer(
                id=f"tp-{row.get('origin')}-{row.get('destination')}-{outbound}-{inbound}",
                kind='FLIGHT',
                provenance=Provenance(provider='Travelpayouts / Aviasales Data API',
                                       access_status=Access.LIVE, pricing_reality=Reality.LIMITED_REAL,
                                       bookable=None, source_url=SOURCE_URL, fetched_at=fetched),
                price=Money(original_amount=amount, original_currency=currency.upper()),
                search_url=search_url,
                origin=str(row.get('origin') or ''),
                destination=str(row.get('destination') or ''),
                departure_date=outbound,
                return_date=inbound,
                passenger_price_scope='Кэшированная цена одного билета; состав семьи и багаж этим API не подтверждены.',
                raw_reference=f"{row.get('origin')}\u2192{row.get('destination')} \u00b7 {row.get('departure_at')}"
                               f"{' \u00b7 ' + str(row.get('return_at')) if row.get('return_at') else ''}"
                               f" \u00b7 \u043f\u0435\u0440\u0435\u0441\u0430\u0434\u043e\u043a: {row.get('transfers', '?')}",
            ))
        return offers


TRANSFER_STATUS = {
    'kiwitaxi_via_travelpayouts': {
        'note': 'Партнёрская программа подтверждена официально, но это deep-link/виджет '
                'выдачи, а не документированный публичный JSON-эндпоинт с ценами — так что '
                'мы не подключаем сюда «живые» цифры, которые не сможем подтвердить.',
        'docs_url': 'https://support.travelpayouts.com/hc/en-us/articles/20384016664594',
    },
}

HOTEL_LIVE_SEARCH_STATUS = {
    'note': 'Бесплатный self-serve доступ есть только для поиска отеля/локации по имени '
            '(без цен). Живой поиск с ценами (Hotellook Hotel Search API) выдаётся по '
            'индивидуальному запросу — нужно написать в поддержку Travelpayouts с описанием '
            'проекта и макетами, прежде чем появится ключ для реальных цен.',
    'docs_url': 'https://support.travelpayouts.com/hc/en-us/articles/203956133-Hotel-search-API',
}
