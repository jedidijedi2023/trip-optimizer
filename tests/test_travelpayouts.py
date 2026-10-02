import os
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.providers.travelpayouts import AviasalesFlightData, travelpayouts_token
from backend.providers.live_search import _bool_travelpayouts, _travelpayouts_offers


class TravelpayoutsTests(unittest.IsolatedAsyncioTestCase):
    def test_render_secret_file_counts_as_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / 'TRAVELPAYOUTS_TOKEN'
            secret.write_text('TRAVELPAYOUTS_TOKEN=own-test-token\n', encoding='utf-8')
            with patch.dict(os.environ, {'TRAVELPAYOUTS_TOKEN': ''}), \
                 patch('backend.providers.travelpayouts.SECRET_PATH', secret):
                self.assertEqual(travelpayouts_token(), 'own-test-token')
                self.assertTrue(_bool_travelpayouts())

    async def test_normalizes_cached_round_trip_without_exposing_token(self):
        depart = date.today() + timedelta(days=10)
        returned = depart + timedelta(days=9)
        response = {'response': {'success': True, 'data': [
            {'origin': 'SVO', 'destination': 'HKT', 'departure_at': str(depart),
             'return_at': str(returned), 'price': 40000, 'link': '/search/SVO...', 'transfers': 1},
            {'origin': 'SVO', 'destination': 'HKT', 'departure_at': str(depart),
             'price': 12000},
            'invalid',
        ]}}
        with patch.dict(os.environ, {'TRAVELPAYOUTS_TOKEN': 'private-test-token'}), \
             patch('backend.providers.travelpayouts.http.request', new_callable=AsyncMock, return_value=response) as request:
            offers = await AviasalesFlightData().prices_for_dates('SVO', departure_at=depart.strftime('%Y-%m'))
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0].price.original_amount, 40000)
        self.assertEqual(offers[0].search_url, 'https://www.aviasales.ru/search/SVO...')
        self.assertEqual(offers[0].provenance.pricing_reality.value, 'LIMITED_REAL')
        self.assertIsNone(offers[0].provenance.bookable)
        self.assertEqual(request.call_args.kwargs['headers']['X-Access-Token'], 'private-test-token')
        self.assertNotIn('token', request.call_args.kwargs['params'])

    async def test_search_excludes_other_countries_and_dates(self):
        depart = date.today() + timedelta(days=10)
        returned = depart + timedelta(days=9)
        response = {'response': {'success': True, 'data': [
            {'origin': 'SVO', 'destination': 'HKT', 'departure_at': str(depart), 'return_at': str(returned), 'price': 40000},
            {'origin': 'SVO', 'destination': 'HRG', 'departure_at': str(depart), 'return_at': str(returned), 'price': 45000},
            {'origin': 'SVO', 'destination': 'HRG', 'departure_at': str(depart + timedelta(days=20)),
             'return_at': str(returned + timedelta(days=20)), 'price': 43000},
        ]}}
        filters = {'earliest': str(depart), 'latestDeparture': str(depart + timedelta(days=3)),
                   'latest': str(returned + timedelta(days=3)), 'minNights': 8, 'maxNights': 10,
                   'destinationMode': 'Выбранные страны', 'destinations': 'EG'}
        with patch.dict(os.environ, {'TRAVELPAYOUTS_TOKEN': 'private-test-token'}), \
             patch('backend.providers.travelpayouts.http.request', new_callable=AsyncMock, return_value=response):
            offers, note = await _travelpayouts_offers('SVO', filters)
        self.assertIsNone(note)
        self.assertEqual([(offer.destination, offer.country_code) for offer in offers], [('HRG', 'EG')])

    async def test_targeted_fallback_finds_beach_hidden_by_origin_page_limit(self):
        depart = date.today() + timedelta(days=10)
        returned = depart + timedelta(days=9)
        filters = {'earliest': str(depart), 'latestDeparture': str(depart + timedelta(days=2)),
                   'latest': str(returned + timedelta(days=2)), 'minNights': 8, 'maxNights': 10,
                   'destinationMode': 'Выбранные страны', 'destinations': 'Таиланд'}

        async def response(*args, **kwargs):
            rows = [{'origin': 'SVO', 'destination': 'HKT', 'departure_at': str(depart),
                     'return_at': str(returned), 'price': 48000}]
            return {'response': {'success': True, 'data': rows if kwargs['params'].get('destination') == 'HKT' else []}}

        with patch.dict(os.environ, {'TRAVELPAYOUTS_TOKEN': 'private-test-token'}), \
             patch('backend.providers.travelpayouts.http.request', new_callable=AsyncMock, side_effect=response) as request:
            offers, _ = await _travelpayouts_offers('SVO', filters)
        self.assertEqual([(offer.destination, offer.country_code) for offer in offers], [('HKT', 'TH')])
        self.assertTrue(any(call.kwargs['params'].get('destination') == 'HKT' for call in request.call_args_list))
