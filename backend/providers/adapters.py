import hashlib
import os
import time
import httpx
from datetime import date, timedelta
from backend.models.domain import Access, Reality, Provenance, NormalizedOffer, Money
from backend.providers.base import Provider, ProviderUnavailable, Capability, RestrictedAdapter
from backend.providers.http import http
from backend.providers.public_demo import DIDA_TEST_USER,DIDA_TEST_PASSWORD,TRAVELGATE_TEST_KEY
from backend.providers.normalize import hotelx_offers,duffel_offers

TRAVELGATE_DOC='https://docs.travelgate.com/docs/apis/for-buyers/hotel-x-pull-buyers-api/quickstart/'
TRAVELGATE_DEMO_HOTELS=['ES284122','BR1518']
HOTELX_QUERY='''query DemoSearch($criteriaSearch: HotelCriteriaSearchInput, $settings: HotelSettingsInput, $filterSearch: HotelXFilterSearchInput) {
  hotelX { search(criteria: $criteriaSearch, settings: $settings, filterSearch: $filterSearch) {
    options { id accessCode supplierCode hotelCode hotelName boardCode paymentType status
      occupancies { id paxes { age } } rooms { code description }
      price { currency net gross } cancelPolicy { refundable cancelPenalties { deadline penaltyType currency value } }
    } errors { code type description } warnings { code type description }
  } }
}'''


class TravelgateDemo(Provider):
    name='Travelgate HOTELTEST';capabilities={Capability.HOTEL}
    async def raw_search(self,query):
        checkin=query.get('check_in',str(date.today()+timedelta(days=30)))
        checkout=query.get('check_out',str(date.fromisoformat(checkin)+timedelta(days=1)))
        body={'query':HOTELX_QUERY,'variables':{'criteriaSearch':{'checkIn':checkin,'checkOut':checkout,'hotels':TRAVELGATE_DEMO_HOTELS,
          'occupancies':[{'paxes':[{'age':30} for _ in range(query.get('adults',2))]+[{'age':age} for age in query.get('children',[])]}],'currency':'EUR','markets':['ES'],'language':'en','nationality':query.get('nationality','RU')},
          'settings':{'client':'client_demo','testMode':True,'timeout':10000},
          'filterSearch':{'access':{'includes':['2']}}}}
        return await http.request('travelgate-demo','POST','https://api.travelgate.com',json_body=body,headers={'Authorization':'Apikey '+TRAVELGATE_TEST_KEY,'Accept-Encoding':'gzip'},ttl=300)
    async def search(self,query):
        r=await self.raw_search(query)
        return hotelx_offers(r['response'],Provenance(provider=self.name,access_status=Access.DEMO,pricing_reality=Reality.SYNTHETIC,bookable=False,source_url=TRAVELGATE_DOC,fetched_at=r['fetched_at'],expires_at=r['expires_at']))


class DidaTest(Provider):
    name='DidaTravel official test';capabilities={Capability.HOTEL}
    async def countries(self):
        return await http.request('dida-test','GET','https://static-apiint.didatravel.com/api/v1/region/countries',params={'language':'en-US'},auth=(DIDA_TEST_USER,DIDA_TEST_PASSWORD),ttl=86400)
    async def raw_search(self,query):
        # Price Search docs explicitly revoke the shared test account (note 15).
        # Content read succeeded, but that does not authorize using it for rates.
        if not os.getenv('DIDA_CLIENT_ID') or not os.getenv('DIDA_LICENSE_KEY'):
            raise ProviderUnavailable('REGISTRATION_REQUIRED: Dida retired shared PriceSearch account; dedicated test account required')
        if os.getenv('DIDA_ENVIRONMENT')!='sandbox':
            raise ProviderUnavailable('Dedicated Dida account must be explicitly marked sandbox')
        checkin=query.get('check_in',str(date.today()+timedelta(days=30)))
        body={'Header':{'ClientID':os.environ['DIDA_CLIENT_ID'],'LicenseKey':os.environ['DIDA_LICENSE_KEY']},'CheckInDate':checkin,
              'CheckOutDate':query.get('check_out',str(date.fromisoformat(checkin)+timedelta(days=1))),
              'HotelIDList':[5982,11,7017,239133,1672],'LowestPriceOnly':True,'Nationality':query.get('nationality','RU'),'Currency':'USD'}
        return await http.request('dida-test','POST','https://apiint.didatravel.com/api/rate/pricesearch',params={'$format':'json'},json_body=body,ttl=300)
    async def search(self,query):
        r=await self.raw_search(query)
        # Preserve unknown schemas rather than making up a price mapping.
        from backend.providers.dida_normalize import dida_offers
        return dida_offers(r['response'],Provenance(provider=self.name,access_status=Access.SANDBOX,pricing_reality=Reality.SYNTHETIC,bookable=False,source_url='https://apidoc.didatravel.com/booking-api/price-search.html',fetched_at=r['fetched_at'],expires_at=r['expires_at']))


class HotelbedsEvaluation(Provider):
    name='Hotelbeds Evaluation';capabilities={Capability.HOTEL}
    def headers(self):
        key=os.getenv('HOTELBEDS_API_KEY');secret=os.getenv('HOTELBEDS_SECRET')
        if not key or not secret:raise ProviderUnavailable('REGISTRATION_REQUIRED: Hotelbeds Evaluation key and secret')
        return {'Api-key':key,'X-Signature':hashlib.sha256((key+secret+str(int(time.time()))).encode()).hexdigest(),'Accept':'application/json'}
    async def status(self):
        return await http.request('hotelbeds-evaluation','GET','https://api.test.hotelbeds.com/hotel-api/1.0/status',headers=self.headers())
    async def search(self,query):
        # Evaluation wire search requires hotel codes and exact occupancy; no booking call exists.
        if not query.get('hotel_codes'):raise ValueError('Authorized hotel codes required')
        body={'stay':{'checkIn':query['check_in'],'checkOut':query['check_out']},'occupancies':query['occupancies'],'hotels':{'hotel':query['hotel_codes']}}
        r=await http.request('hotelbeds-evaluation','POST','https://api.test.hotelbeds.com/hotel-api/1.0/hotels',headers=self.headers(),json_body=body)
        if r['response'].get('error'):raise ProviderUnavailable('Hotelbeds evaluation rejected request')
        from backend.providers.hotelbeds_normalize import hotelbeds_offers
        return hotelbeds_offers(r['response'],Provenance(provider=self.name,access_status=Access.EVALUATION,pricing_reality=Reality.SYNTHETIC,bookable=False,source_url='https://developer.hotelbeds.com/',fetched_at=r['fetched_at'],expires_at=r['expires_at']))


class DuffelTest(Provider):
    name='Duffel Test';capabilities={Capability.FLIGHT}
    async def search(self,query):
        token=os.getenv('DUFFEL_TOKEN','')
        if not token:raise ProviderUnavailable('REGISTRATION_REQUIRED: Duffel test token')
        if not token.startswith('duffel_test_'):raise ValueError('Only duffel_test_ tokens accepted')
        body={'data':{'slices':query['slices'],'passengers':query['passengers'],'cabin_class':'economy'}}
        r=await http.request('duffel-test','POST','https://api.duffel.com/air/offer_requests',params={'return_offers':'true'},json_body=body,headers={'Authorization':'Bearer '+token,'Duffel-Version':'v2','Accept':'application/json'},ttl=60)
        return duffel_offers(r['response'],Provenance(provider=self.name,access_status=Access.SANDBOX,pricing_reality=Reality.SYNTHETIC,bookable=False,source_url='https://duffel.com/docs/api/overview/test-mode',fetched_at=r['fetched_at'],expires_at=r['expires_at']))


class TourvisorTrial(Provider):
    name='Tourvisor trial';capabilities={Capability.PACKAGE}
    async def countries(self,departure_id:int):
        token=os.getenv('TOURVISOR_TOKEN','')
        if not token:raise ProviderUnavailable('REGISTRATION_REQUIRED: official trial JWT')
        return await http.request('tourvisor-trial','GET','https://api.tourvisor.ru/search/api/v1/countries',params={'departureId':departure_id,'onlyDirect':'true'},headers={'Authorization':'Bearer '+token},ttl=3600)
    async def search(self,query):
        raise ProviderUnavailable('REGISTRATION_REQUIRED: trial activation; package search mapping pending authorized test response')


class MockProvider(Provider):
    name='Local synthetic fixtures';capabilities={Capability.FLIGHT,Capability.HOTEL,Capability.PACKAGE,Capability.CHARTER,Capability.TRANSFER,Capability.FERRY}
    async def search(self,query):
        kind=query.get('kind','HOTEL')
        p=Provenance(provider=self.name,access_status=Access.MOCK,pricing_reality=Reality.SYNTHETIC,bookable=False,source_url='local:synthetic-fixture')
        return [NormalizedOffer(id='mock-'+kind.lower(),kind=kind,provenance=p,price=Money(original_amount='12345.67',original_currency='RUB'))]
    async def details(self,offer_id):
        return (await self.search({'kind':offer_id.removeprefix('mock-').upper()}))[0]
    async def actualize(self,offer_id):
        # Actualization of a mock cannot promote availability or pricing reality.
        return await self.details(offer_id)


restricted={
 name:RestrictedAdapter(name,caps,status,url) for name,caps,status,url in [
 ('RateHawk',[Capability.HOTEL],Access.REGISTRATION_REQUIRED,'https://www.ratehawk.com/lp/en/API/'),
 ('WebBeds',[Capability.HOTEL],Access.COMMERCIAL_CONTRACT_REQUIRED,'https://www.webbeds.com/buyers/support/'),
 ('TBO',[Capability.HOTEL],Access.COMMERCIAL_CONTRACT_REQUIRED,'https://demo.tbo.com/tbo-api'),
 ('AviaCenter',[Capability.CHARTER,Capability.FLIGHT],Access.COMMERCIAL_CONTRACT_REQUIRED,'https://aviacenter.ru/partnering/charters/'),
 ('Expedia Rapid',[Capability.HOTEL],Access.REGISTRATION_REQUIRED,'https://developers.expediagroup.com/rapid/setup'),
 ('Amadeus',[Capability.FLIGHT],Access.COMMERCIAL_CONTRACT_REQUIRED,'https://github.com/amadeus4dev/developer-guides')]
}


async def with_mock_fallback(provider,query):
    try:return {'offers':await provider.search(query),'fallback':False,'reason':None}
    except (ProviderUnavailable,ValueError,httpx.HTTPError) as exc:
        return {'offers':await MockProvider().search(query),'fallback':True,'reason':str(exc)}
