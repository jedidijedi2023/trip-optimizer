import os
import unittest
from datetime import date,timedelta
from unittest.mock import patch,AsyncMock
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.providers.validation_search import ValidationSearch,validation_search,ratehawk_offers,tourvisor_offers,provenance
from backend.providers.adapters import TravelgateDemo
from backend.providers.http import SafeHTTP
from backend.models.domain import Access,Reality

class ValidationTests(unittest.IsolatedAsyncioTestCase):
    def payload(self,**kw):return {'check_in':str(date.today()+timedelta(days=30)),**kw}
    async def test_all_fifteen_offline_distinct_fixtures(self):
        from backend.providers.validation_search import NAMES
        result=await validation_search(ValidationSearch(**self.payload(providers=list(NAMES),date_samples=3,network=False,children=[5,7,9])))
        self.assertEqual(len(result['results']),45)
        ids=set()
        for r in result['results']:
            self.assertTrue(r['fallback']);self.assertEqual(r['access_status'],'MOCK')
            o=r['offers'][0];ids.add(o.id)
            self.assertFalse(o.provenance.bookable);self.assertEqual(o.provenance.pricing_reality,Reality.SYNTHETIC)
            self.assertEqual(o.occupancy[0]['children'],[5,7,9])
        self.assertEqual(len(ids),45);self.assertIsNone(result['economic_validation']['savings'])
    async def test_missing_keys_no_network(self):
        with patch.dict(os.environ,{},clear=True),patch('backend.providers.validation_search.http.request',new_callable=AsyncMock) as request:
            result=await validation_search(ValidationSearch(**self.payload(providers=['ratehawk','duffel','tourvisor','hotelbeds'])))
            request.assert_not_called();self.assertTrue(all(r['fallback'] for r in result['results']))
    async def test_travelgate_sends_exact_family_and_dates(self):
        response={'response':{'data':{'hotelX':{'search':{'options':[]}}}},'fetched_at':'2026-09-19T00:00:00+00:00','expires_at':'2026-09-19T00:05:00+00:00'}
        with patch('backend.providers.adapters.http.request',new_callable=AsyncMock,return_value=response) as request:
            await TravelgateDemo().search({'check_in':'2026-10-20','check_out':'2026-10-27','adults':2,'children':[5,7,9]})
            variables=request.call_args.kwargs['json_body']['variables']
            self.assertEqual([p['age'] for p in variables['criteriaSearch']['occupancies'][0]['paxes']],[30,30,5,7,9])
            self.assertEqual(variables['criteriaSearch']['hotels'],['ES284122','BR1518'])
            self.assertEqual(variables['criteriaSearch']['checkOut'],'2026-10-27');self.assertTrue(variables['settings']['testMode'])
    async def test_dangerous_operations_not_allowlisted(self):
        for method,url in [('POST','https://api.ratehawk.com/api/b2b/v3/hotel/order/booking/finish/'),('GET','https://api.tourvisor.ru/search/api/v1/tours/search/1/continue'),('POST','https://api.test.hotelbeds.com/hotel-api/1.0/bookings')]:
            with self.assertRaises(ValueError):await SafeHTTP().request('x',method,url)
    def test_catalogue_and_input_validation(self):
        client=TestClient(app)
        self.assertEqual(len(client.get('/api/validation/providers').json()['providers']),15)
        for bad in [{'providers':['evil']},{'date_samples':4},{'children':[18]},{'region_id':999},{'providers':['duffel','duffel']}]:
            self.assertEqual(client.post('/api/validation/search',json=self.payload(**bad)).status_code,422)
    def test_schema_fixtures_no_economic_promotion(self):
        p=provenance('fixture',Access.MOCK,Reality.SYNTHETIC,'local:authored-schema-fixture')
        etg={'status':'ok','data':{'hotels':[{'hid':1,'id':'synthetic','rates':[{'search_hash':'sr-fixture','room_name':'Test','payment_options':{'payment_types':[{'show_amount':'321.45','show_currency_code':'USD','amount':'1000','currency_code':'RUB','tax_data':{'taxes':[{'amount':'10','currency_code':'AED','included_by_supplier':False}]}}]}}]}]}}
        o=ratehawk_offers(etg,p,[{'adults':2,'children':[5]}])[0]
        self.assertEqual(str(o.price.original_amount),'321.45');self.assertEqual(o.price.original_currency,'USD');self.assertFalse(o.mandatory_costs_complete)
        tours=[{'id':1,'name':'Synthetic','tours':[{'id':'test-tour','price':1000,'currency':'RUB','adults':2,'childs':3,'meal':{'name':'AI'}}]}]
        t=tourvisor_offers(tours,p)[0];self.assertEqual(t.kind,'PACKAGE');self.assertFalse(t.provenance.bookable)
        with self.assertRaises(ValueError):tourvisor_offers({'error':'schema changed'},p)
    def test_hotelx_no_inventory_not_mock(self):
        from backend.providers.normalize import hotelx_offers
        p=provenance('HOTELTEST',Access.DEMO,Reality.SYNTHETIC,'local:test')
        d={'data':{'hotelX':{'search':{'options':None,'errors':[{'code':'ALL_PROCESSES_FAILED'}],'warnings':[{'code':'11204'}]}}}}
        self.assertEqual(hotelx_offers(d,p),[])
