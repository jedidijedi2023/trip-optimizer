"""Bounded zero-cost component searches. No live bookings or economic ranking."""
import asyncio
import hashlib
import json
import os
from datetime import date, timedelta
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator
from backend.models.domain import Access, Reality, Provenance, NormalizedOffer, Money, HotelEntity
from backend.providers.adapters import TravelgateDemo, HotelbedsEvaluation, DuffelTest
from backend.providers.base import ProviderUnavailable
from backend.providers.http import http

ProviderId=Literal['tourvisor','aviacenter','hotelbeds','ratehawk','webbeds','tbo','dida','travelgate','expedia','duffel','amadeus','samo','juniper','traveltek','peakwork']
NAMES={'tourvisor':'Tourvisor','aviacenter':'AviaCenter','hotelbeds':'Hotelbeds / HBX','ratehawk':'RateHawk','webbeds':'WebBeds','tbo':'TBO','dida':'DidaTravel','travelgate':'Travelgate HotelX','expedia':'Expedia Rapid','duffel':'Duffel','amadeus':'Amadeus','samo':'SAMO','juniper':'Juniper','traveltek':'Traveltek','peakwork':'Peakwork'}
CONTRACT={'aviacenter','webbeds','tbo','amadeus','samo','juniper','traveltek','peakwork'}

class ValidationSearch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    providers:list[ProviderId]=Field(default_factory=lambda:['travelgate'],min_length=1,max_length=15)
    check_in:date
    nights:int=Field(default=7,ge=1,le=28)
    date_samples:int=Field(default=1,ge=1,le=3)
    adults:int=Field(default=2,ge=1,le=8)
    children:list[int]=Field(default_factory=list,max_length=8)
    nationality:str=Field(default='RU',pattern=r'^[A-Z]{2}$')
    hotelbeds_codes:list[int]=Field(default_factory=list,max_length=10)
    tourvisor_departure:int|None=Field(default=None,ge=1)
    tourvisor_country:int|None=Field(default=None,ge=1)
    flight_origin:str=Field(default='LHR',pattern=r'^[A-Z]{3}$')
    flight_destination:str=Field(default='JFK',pattern=r'^[A-Z]{3}$')
    region_id:int=6053839
    network:bool=True
    @model_validator(mode='after')
    def valid(self):
        if not date.today()<=self.check_in<=date.today()+timedelta(days=365):raise ValueError('Choose a future date within one year')
        if any(type(a) is not int or not 0<=a<=17 for a in self.children):raise ValueError('Child ages must be 0..17')
        if len(set(self.providers))!=len(self.providers):raise ValueError('Duplicate providers')
        if self.region_id not in {2011,2395,2734,6053839}:raise ValueError('Choose a documented RateHawk sandbox region')
        if any(c<=0 for c in self.hotelbeds_codes):raise ValueError('Hotel codes must be positive')
        if self.flight_origin==self.flight_destination:raise ValueError('Flight endpoints must differ')
        return self

def provenance(provider,access,reality,source,r=None):
    timestamps={k:r[k] for k in ['fetched_at','expires_at']} if r else {}
    return Provenance(provider=provider,access_status=access,pricing_reality=reality,bookable=False,source_url=source,**timestamps)

def ratehawk_offers(data,p,occupancy):
    if data.get('status')!='ok' or data.get('error'):raise ProviderUnavailable('RateHawk supplier error')
    offers=[]
    for hotel in (data.get('data') or {}).get('hotels',[]):
        for rate in hotel.get('rates',[]):
            payments=(rate.get('payment_options') or {}).get('payment_types') or []
            # Keep payment alternatives separate; never sum daily and total prices.
            for i,payment in enumerate(payments):
                if payment.get('show_amount') is None or not payment.get('show_currency_code'):continue
                hid=str(hotel['hid']);rid=rate.get('search_hash') or rate.get('match_hash')
                if not rid:continue
                offers.append(NormalizedOffer(id=f'{hid}:{rid}:{i}',kind='HOTEL',provenance=p,
                    price=Money(original_amount=payment['show_amount'],original_currency=payment['show_currency_code']),
                    hotel=HotelEntity(canonical_id='ratehawk:'+hid,name=hotel.get('id',hid),country='UNKNOWN',provider_ids={'ratehawk':hid}),
                    occupancy=occupancy,room=rate.get('room_name'),meal=rate.get('meal'),
                    cancellation=payment.get('cancellation_penalties'),payment_terms=payment.get('type'),raw_reference=rid))
    return offers

async def ratehawk_search(q):
    key_id=os.getenv('RATEHAWK_SANDBOX_KEY_ID');key=os.getenv('RATEHAWK_SANDBOX_KEY')
    if not key_id or not key:raise ProviderUnavailable('REGISTRATION_REQUIRED: own RateHawk sandbox key ID and key')
    guests=[{'adults':q['adults'],'children':q['children']}]
    body={'checkin':q['check_in'],'checkout':q['check_out'],'residency':q['nationality'].lower(),'language':'en','guests':guests,'region_id':q['region_id'],'currency':'USD'}
    r=await http.request('ratehawk-sandbox','POST','https://api-sandbox.ratehawk.com/api/b2b/v3/search/serp/region/',json_body=body,auth=(key_id,key))
    return ratehawk_offers(r['response'],provenance('RateHawk',Access.SANDBOX,Reality.SYNTHETIC,'https://docs.emergingtravel.com/docs/fundamentals/sandbox/',r),guests)

def tourvisor_offers(data,p):
    if not isinstance(data,list):raise ValueError('Unexpected Tourvisor results schema')
    offers=[]
    for hotel in data:
        for tour in hotel.get('tours',[]):
            offers.append(NormalizedOffer(id=str(tour['id']),kind='PACKAGE',provenance=p,
                price=Money(original_amount=tour['price'],original_currency=tour['currency']),
                hotel=HotelEntity(canonical_id='tourvisor:'+str(hotel['id']),name=hotel['name'],country='UNKNOWN',provider_ids={'tourvisor':str(hotel['id'])}),
                room=tour.get('roomType'),meal=(tour.get('meal') or {}).get('name'),
                occupancy=[{'adults':tour.get('adults'),'children_count':tour.get('childs')}],raw_reference=str(tour['id'])))
    return offers

async def tourvisor_search(q):
    token=os.getenv('TOURVISOR_TOKEN')
    if not token or os.getenv('TOURVISOR_ACCESS_MODE')!='trial':raise ProviderUnavailable('REGISTRATION_REQUIRED: own JWT and TOURVISOR_ACCESS_MODE=trial')
    if not q['tourvisor_country'] or not q['tourvisor_departure']:raise ProviderUnavailable('CONFIGURATION_REQUIRED: Tourvisor dictionary departure/country IDs')
    if q['adults']>6 or len(q['children'])>3:raise ProviderUnavailable('OCCUPANCY_UNSUPPORTED: Tourvisor maximum 6 adults and 3 children')
    headers={'Authorization':'Bearer '+token}
    params={'departureId':q['tourvisor_departure'],'countryId':q['tourvisor_country'],'dateFrom':q['check_in'],'dateTo':q['check_in'],'nightsFrom':q['nights'],'nightsTo':q['nights'],'adults':q['adults'],'childs':q['children'],'currency':'RUB','onlyCharter':'false'}
    start=await http.request('tourvisor-trial','GET','https://api.tourvisor.ru/search/api/v1/tours/search',params=params,headers=headers,ttl=300)
    search_id=start['response'].get('searchId')
    if type(search_id) is not int or search_id<=0:raise ValueError('Invalid search ID')
    # Bounded initial snapshot. Empty results can mean search is still running, not no inventory.
    r=await http.request('tourvisor-trial','GET',f'https://api.tourvisor.ru/search/api/v1/tours/search/{search_id}',params={'limit':25},headers=headers,ttl=5)
    return tourvisor_offers(r['response'],provenance('Tourvisor',Access.TRIAL,Reality.UNKNOWN,'https://api.tourvisor.ru/search/docs',r))

def fixture(provider,q):
    kind='FLIGHT' if provider in {'duffel','amadeus','aviacenter'} else 'PACKAGE' if provider in {'tourvisor','samo','traveltek','peakwork'} else 'HOTEL'
    digest=hashlib.sha256(json.dumps([provider,q],sort_keys=True).encode()).hexdigest()[:16]
    # Internal fixture, intentionally not advertised as a vendor sample response.
    amount=(100+int(digest[:4],16)%50)*q['nights']*(q['adults']+len(q['children'])/2)
    return NormalizedOffer(id='fixture:'+provider+':'+digest,kind=kind,
        provenance=provenance(NAMES[provider]+' — local fixture',Access.MOCK,Reality.SYNTHETIC,'local:validation-fixture'),
        price=Money(original_amount=str(amount),original_currency='USD'),
        occupancy=[{'adults':q['adults'],'children':q['children']}])

async def component(provider,q,network):
    status='DEMO' if provider in {'travelgate','samo'} else 'COMMERCIAL_CONTRACT_REQUIRED' if provider in CONTRACT else 'REGISTRATION_REQUIRED'
    reason='Provider adapter awaits authorized onboarding; local internal fixture only'
    try:
        if not network:raise ProviderUnavailable('OFFLINE: local fixture requested')
        if provider=='travelgate':offers=await TravelgateDemo().search(q)
        elif provider=='ratehawk':offers=await ratehawk_search(q)
        elif provider=='tourvisor':offers=await tourvisor_search(q)
        elif provider=='hotelbeds':
            if not q['hotelbeds_codes']:raise ProviderUnavailable('CONFIGURATION_REQUIRED: own Evaluation keys and hotel codes')
            occupancies=[{'rooms':1,'adults':q['adults'],'children':len(q['children']),'paxes':[{'type':'CH','age':a} for a in q['children']]}]
            offers=await HotelbedsEvaluation().search({**q,'hotel_codes':q['hotelbeds_codes'],'occupancies':occupancies})
        elif provider=='duffel':
            passengers=[{'type':'adult'} for _ in range(q['adults'])]+[{'age':a} for a in q['children']]
            slices=[{'origin':q['flight_origin'],'destination':q['flight_destination'],'departure_date':q['check_in']},{'origin':q['flight_destination'],'destination':q['flight_origin'],'departure_date':q['check_out']}]
            offers=await DuffelTest().search({'slices':slices,'passengers':passengers})
        elif provider=='samo':raise ProviderUnavailable('DEMO_ONLY: UI login validated; no authorized SAMO API contract, local fixture only')
        else:raise ProviderUnavailable(reason)
        return {'provider':provider,'name':NAMES[provider],'query':q,'fallback':False,'access_status':offers[0].provenance.access_status if offers else {'travelgate':'DEMO','tourvisor':'TRIAL','hotelbeds':'EVALUATION'}.get(provider,'SANDBOX'),'offers':offers,
            'note':'Bounded search snapshot; empty does not prove no inventory. Test geography is provider-specific. Taxes and actualization incomplete.'}
    except ProviderUnavailable as exc:reason=str(exc)
    except Exception as exc:
        # Never echo supplier bodies, authentication strings or URLs containing secrets.
        reason='UPSTREAM_UNAVAILABLE: '+type(exc).__name__
    return {'provider':provider,'name':NAMES[provider],'query':q,'fallback':True,'access_status':'MOCK','upstream_access_status':status,'offers':[fixture(provider,q)],'note':reason}

async def validation_search(request:ValidationSearch):
    results=[]
    for offset in range(request.date_samples):
        q=request.model_dump(exclude={'providers','date_samples','network'},mode='json')
        q['check_in']=str(request.check_in+timedelta(days=offset));q['check_out']=str(request.check_in+timedelta(days=offset+request.nights))
        # Limit concurrent suppliers; each supplier has its own 1 QPS HTTP guard.
        for start in range(0,len(request.providers),3):
            results.extend(await asyncio.gather(*(component(p,q,request.network) for p in request.providers[start:start+3])))
    return {'mode':'ZERO_COST_VALIDATION','results':results,'economic_validation':{'comparable_real_offers':0,'savings':None},
        'limitations':['Component tests, not complete family itineraries','One room, constant occupancy; split-family stays are not submitted','Travelgate fixed demo hotels ES284122 and BR1518; RateHawk uses selected sandbox region','No booking, payment, commercial ranking or automatic production access']}
