import asyncio
import unittest
from dataclasses import replace
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal
from pydantic import ValidationError
from backend.models.domain import *
from backend.pricing.engine import total_cost,convert,economically_comparable,real_savings
from backend.search.dates import flexible_dates,occupancy_intervals
from backend.routing.engine import Leg,validate_timeline,recommended_buffer,booking_risk
from backend.hotels.matching import match_hotels
from backend.gateway.optimizer import eligible_gateways,GatewayCandidate
from backend.providers.adapters import MockProvider,restricted,with_mock_fallback,DuffelTest,DidaTest
from backend.providers.normalize import normalized_package,hotelx_offers,duffel_offers
from backend.providers.http import SafeHTTP
from backend.scoring.quality import total_score
from backend.visa.engine import VisaRuleEngine,VisaProfile,Visit
from tests.test_visa import rule,NOW,DAY

def provenance(**kwargs):
    now=datetime.now(timezone.utc)
    return Provenance(**({'provider':'fixture','access_status':'MOCK','pricing_reality':'SYNTHETIC','bookable':False,'source_url':'local:test','fetched_at':now,'expires_at':now+timedelta(hours=1)}|kwargs))

def cost(id,amount,currency='RUB',**kwargs):
    return CostLine(id=id,category=id,money=Money(original_amount=amount,original_currency=currency),provenance=provenance(),**kwargs)

def window():
    return SearchWindow(earliest=date(2026,10,18),latest_departure=date(2026,10,20),latest_return=date(2026,11,30),
        travellers=[Traveller(id='a1',age=35),Traveller(id='a2',age=35),Traveller(id='c5',age=5),Traveller(id='c7',age=7),Traveller(id='c9',age=9)],
        groups=[TravellerGroup(name='A',traveller_ids=['a2','c7','c9'],min_nights=9,max_nights=9),TravellerGroup(name='B',traveller_ids=['a1','c5'],min_nights=18,max_nights=18)])

class PricingTests(unittest.TestCase):
    def test_decimal_and_included_baggage(self):
        self.assertEqual(total_cost([cost('package','100.10'),cost('bag','20',included_in='package'),cost('tax','0.20')]),Decimal('100.30'))
    def test_missing_fx_and_duplicate_components(self):
        with self.assertRaises(ValueError):total_cost([cost('hotel','100','EUR')])
        with self.assertRaises(ValueError):total_cost([cost('x','1'),cost('x','2')])
    def test_fx_records_original_and_source(self):
        m=convert(Money(original_amount='1.11',original_currency='EUR'),Decimal('101.25'),'TEST',NOW)
        self.assertEqual(m.converted_amount,Decimal('112.39'));self.assertEqual(m.original_amount,Decimal('1.11'))
    def test_synthetic_never_economic(self):
        for access in ('MOCK','SANDBOX','DEMO','EVALUATION','TRIAL'):
            line=cost('x','100');line.provenance=provenance(access_status=access)
            self.assertFalse(economically_comparable([line],complete=True))
            self.assertIsNone(real_savings([line],[line],candidate_key='a',baseline_key='a',complete=True))
    def test_mixed_real_and_synthetic_rejected(self):
        real=cost('real','100');real.provenance=provenance(access_status='LIVE',pricing_reality='REAL',bookable=True)
        self.assertTrue(economically_comparable([real],complete=True))
        self.assertFalse(economically_comparable([real,cost('mock','1')],complete=True))
        self.assertIsNone(real_savings([real],[real],candidate_key='different',baseline_key='dates',complete=True))
    def test_bookable_guard(self):
        with self.assertRaises(ValidationError):provenance(bookable=True)
    def test_expired_live_quote_rejected(self):
        line=cost('x','100');line.provenance=provenance(access_status='LIVE',pricing_reality='REAL',bookable=True,expires_at=NOW)
        self.assertFalse(economically_comparable([line],complete=True,now=NOW))

class FamilyTests(unittest.TestCase):
    def test_common_outbound_split_return_and_occupancy(self):
        w=window();scenarios=list(flexible_dates(w));self.assertEqual(len(scenarios),3)
        s=scenarios[0]
        self.assertEqual(s['returns']['A'],date(2026,10,27));self.assertEqual(s['returns']['B'],date(2026,11,5))
        periods=occupancy_intervals(w,s)
        self.assertEqual(len(periods[0]['traveller_ids']),5);self.assertEqual(set(periods[1]['traveller_ids']),{'a1','c5'})
        self.assertEqual([p['nights'] for p in periods],[9,9])
    def test_no_unaccompanied_or_duplicate_children(self):
        data=window().model_dump();data['groups'][0]['traveller_ids']=['c7','c9']
        with self.assertRaises(ValidationError):SearchWindow(**data)
    def test_latest_return_and_scenario_budget(self):
        w=window().model_copy(update={'latest_return':date(2026,10,28)})
        self.assertEqual(list(flexible_dates(w)),[])
        with self.assertRaises(ValueError):list(flexible_dates(window(),limit=2))

class RouteTests(unittest.TestCase):
    def test_conservative_buffer(self):
        self.assertEqual(recommended_buffer(children=True,international_self_transfer=True),24)
        self.assertGreater(recommended_buffer(children=True,bag_recheck=True,airport_change=True),24)
    def test_overlap_and_missing_transfer(self):
        a=Leg('a','MOW','IST',NOW,NOW+timedelta(hours=5),('a1',))
        b=Leg('b','IST','DPS',NOW+timedelta(hours=6),NOW+timedelta(hours=18),('a1',),separate_ticket=True)
        with self.assertRaises(ValueError):validate_timeline([a,b],children=True)
        b=replace(b,departure=NOW+timedelta(hours=30),arrival=NOW+timedelta(hours=42))
        self.assertEqual(len(validate_timeline([a,b],children=True)),2)
        with self.assertRaises(ValueError):validate_timeline([a,replace(b,origin='SAW')])
    def test_gateway_five_countries_require_evidence(self):
        countries=[('TR','IST'),('AE','DXB'),('QA','DOH'),('OM','MCT'),('CN','PEK')]
        candidates=[GatewayCandidate(ap,c,Decimal('50000'),5,24,7,True,True,True,[Visit(c,DAY,DAY,role='gateway')]) for c,ap in countries]
        accepted,rejected=eligible_gateways(candidates,VisaRuleEngine(),VisaProfile(),now=NOW)
        self.assertEqual(len(accepted),0);self.assertEqual(len(rejected),5)
        accepted,_=eligible_gateways(candidates,VisaRuleEngine([rule(c) for c,_ in countries]),VisaProfile(),now=NOW)
        self.assertEqual(len(accepted),5)
    def test_unknown_booking_high_risk(self):self.assertEqual(booking_risk()['level'],'HIGH')

class MatchingTests(unittest.TestCase):
    def hotel(self,**kw):return HotelEntity(**({'canonical_id':'a','name':'Resort Test','country':'TR'}|kw))
    def test_fuzzy_never_merges(self):self.assertFalse(match_hotels(self.hotel(),self.hotel())['auto_merge'])
    def test_giata_conflict_wins(self):
        self.assertFalse(match_hotels(self.hotel(giata_id='1'),self.hotel(giata_id='2'))['auto_merge'])
        self.assertTrue(match_hotels(self.hotel(giata_id='1'),self.hotel(giata_id='1'))['auto_merge'])
    def test_missing_weather_not_perfect(self):self.assertIsNone(total_score({'weather':None},{'weather':30}))

class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_fallback_does_not_claim_real(self):
        r=await with_mock_fallback(restricted['AviaCenter'],{'kind':'CHARTER'})
        self.assertTrue(r['fallback']);self.assertFalse(r['offers'][0].provenance.bookable)
        self.assertEqual(r['offers'][0].provenance.pricing_reality,Reality.SYNTHETIC)
    async def test_mock_actualization_never_promotes(self):
        self.assertFalse((await MockProvider().actualize('mock-hotel')).provenance.bookable)
    async def test_writes_blocked(self):
        h=SafeHTTP()
        with self.assertRaises(ValueError):await h.request('x','POST','https://api.duffel.com/air/orders')
        with self.assertRaises(ValueError):await h.request('x','POST','https://api.travelgate.com',json_body={'query':'mutation Book {book{id}}'})
    async def test_travelgate_demo_scope_is_fixed(self):
        h=SafeHTTP()
        body={'query':'query DemoSearch { hotelX { search { options { id } } } }','variables':{
            'settings':{'client':'client_demo','testMode':True},
            'filterSearch':{'access':{'includes':['2']}},
            'criteriaSearch':{'hotels':['NOT_DOCUMENTED']}}}
        with self.assertRaisesRegex(ValueError,'documented HOTELTEST'):
            await h.request('x','POST','https://api.travelgate.com',json_body=body)
    def test_flight_hotel_package_normalization(self):
        p=provenance()
        flights=duffel_offers({'data':{'offers':[{'id':'test','live_mode':False,'total_amount':'123.45','total_currency':'EUR','slices':[{'segments':[{'origin':{'iata_code':'SVO','time_zone':'Europe/Moscow'},'destination':{'iata_code':'IST','time_zone':'Europe/Istanbul'},'departing_at':'2026-10-18T08:00:00','arriving_at':'2026-10-18T13:00:00'}]}]}]}},p)
        self.assertEqual(flights[0].flights[0].departure.utcoffset(),timedelta(hours=3))
        hotels=hotelx_offers({'data':{'hotelX':{'search':{'options':[{'id':'hotel','hotelCode':'TEST','hotelName':'Synthetic','price':{'net':10,'gross':None,'currency':'EUR'},'boardCode':'BB'}]}}}},p)
        self.assertEqual(hotels[0].price.original_amount,10)
        package=normalized_package({'id':'p','price':{'original_amount':100,'original_currency':'RUB'},'hotel':hotels[0].hotel.model_dump(),'meal':'AI'},p)
        self.assertEqual(package.kind,'PACKAGE');self.assertFalse(package.provenance.bookable)

if __name__=='__main__':unittest.main()
