import unittest
from unittest.mock import AsyncMock,patch

from backend.models.domain import SearchSourceSettings
from backend.providers.live_search import gather_live_offers


class GracefulProviderFailureTests(unittest.IsolatedAsyncioTestCase):
    async def test_b2b_failure_does_not_cancel_retail(self):
        settings=SearchSourceSettings(search_tour_operators=False,search_wholesalers=True,search_retail_diy=True)
        filters={'earliest':'2026-11-01','latestDeparture':'2026-11-02','latest':'2026-11-20','minNights':7,'maxNights':14,'airports':'SVO','destinationMode':'Выбранные страны','destinations':'TH'}
        with patch('backend.providers.live_search.TravelgateDemo.search',new_callable=AsyncMock,side_effect=TimeoutError), \
             patch('backend.providers.live_search._bool_ratehawk',return_value=False), \
             patch('backend.providers.live_search._bool_travelpayouts',return_value=True), \
             patch('backend.providers.live_search._travelpayouts_offers',new_callable=AsyncMock,return_value=([],None)) as retail:
            result=await gather_live_offers(filters,{'adults':2,'children':[5,7,9]},settings)
        retail.assert_awaited_once()
        by_name={a['provider']:a for a in result['attempted']}
        self.assertIn('UPSTREAM_UNAVAILABLE',by_name['Travelgate HOTELTEST']['note'])
        self.assertTrue(by_name['Travelpayouts / Aviasales Data API']['used'])
        self.assertEqual(result['offers'],[])

    async def test_disabled_provider_is_not_called(self):
        settings=SearchSourceSettings(search_tour_operators=False,search_wholesalers=False,search_retail_diy=False)
        with patch('backend.providers.live_search.TravelgateDemo.search',new_callable=AsyncMock) as b2b, \
             patch('backend.providers.live_search._travelpayouts_offers',new_callable=AsyncMock) as retail:
            result=await gather_live_offers({}, {}, settings)
        b2b.assert_not_awaited()
        retail.assert_not_awaited()
        self.assertEqual(result['offers'],[])
