from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date,datetime,timezone
import os
import uuid
import json
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2]/'.env')
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from backend.providers.registry import provider_registry
from backend.providers.adapters import TravelgateDemo,DidaTest,MockProvider
from backend.providers.http import http
from backend.providers.base import ProviderUnavailable
from backend.visa.engine import VisaProfile,Visit,VisaRuleEngine
from backend.models.domain import SearchWindow,SearchSourceSettings
from backend.search.dates import flexible_dates,occupancy_intervals
from backend import storage
from backend.pricing.fx import cbr_reference_rates
from backend.providers.validation_search import ValidationSearch,validation_search
from backend.providers.live_search import gather_live_offers

@asynccontextmanager
async def lifespan(app):
    try:app.state.database=storage.initialize_storage()
    except Exception:app.state.database=False
    yield

app=FastAPI(title='Global Travel Optimizer',version='0.1.0',lifespan=lifespan,description='DEMO-FIRST, read/search only. No booking or payment endpoints.')
app.add_middleware(CORSMiddleware,allow_origins=['http://127.0.0.1:3000','http://localhost:3000']+[origin.strip() for origin in os.getenv('FRONTEND_ORIGINS','').split(',') if origin.strip()],allow_methods=['GET','POST'],allow_headers=['Content-Type'])

class SearchRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filters:dict=Field(default_factory=dict)
    party:dict=Field(default_factory=dict)
    source_settings:SearchSourceSettings=Field(default_factory=SearchSourceSettings)

GATEWAY_PRIORITY=(('TR','IST'),('AE','DXB'),('QA','DOH'),('OM','MCT'),('CN','PEK'),('GE','TBS'),('AM','EVN'),('AZ','GYD'),('KZ','ALA'),('UZ','TAS'),('RS','BEG'))

def source_orchestration(request:SearchRequest):
    f=request.filters;s=request.source_settings
    enabled=[]
    if s.search_tour_operators and s.search_russian_operators:enabled.append({'group':'RUSSIAN_TOUR_OPERATORS','providers':['Tourvisor','SAMO'],'components':['package']})
    if s.search_wholesalers:enabled.append({'group':'WHOLESALERS_B2B','providers':['HBX','RateHawk','WebBeds','TBO','DidaTravel','Travelgate HotelX','Expedia Rapid'],'components':['flight','hotel','transfer','ferry','bus','charter/block seats']})
    if s.search_retail_diy:enabled.append({'group':'RETAIL_DIY','providers':['Duffel','public/deeplink retail sources'],'components':['flight','hotel','transfer']})
    candidates=[]
    foreign_requested=s.search_tour_operators and s.search_foreign_operators and s.allow_foreign_package_positioning
    if foreign_requested:
        try:arrival=date.fromisoformat(str(f.get('earliest',date.today().isoformat())))
        except ValueError:arrival=date.today()
        try:departure=date.fromisoformat(str(f.get('latest',arrival.isoformat())))
        except ValueError:departure=arrival
        profile=VisaProfile(citizenship=str(f.get('citizenship','RU')),passport=str(f.get('passport','ordinary')),schengen=bool(f.get('schengen',False)),uk=bool(f.get('uk',False)),usa=bool(f.get('usa',False)),canada=bool(f.get('canada',False)),other_visas=[x.strip().upper() for x in str(f.get('otherVisas','')).split(',') if x.strip()],allow_voa=bool(f.get('voa',True)),allow_evisa=bool(f.get('evisa',True)),allow_new_visa=bool(f.get('newVisa',False)),max_visa_cost=float(f.get('visaCost',20000)),max_processing_days=int(f.get('visaDays',7)),allow_airside_schengen=bool(f.get('airside',False)))
        engine=VisaRuleEngine()
        for country,airport in GATEWAY_PRIORITY:
            assessment=engine.assess(profile,[Visit(country,arrival,departure,role='gateway',airport=airport,passport_control=True,separate_tickets=True,overnight=s.positioning_overnight_allowed)])
            candidates.append({'country':country,'airport':airport,'eligible':assessment.allowed,'visa_status':assessment.status.value,'reasons':assessment.reasons})
        enabled.append({'group':'FOREIGN_TOUR_OPERATORS','providers':['foreign package providers'],'components':['positioning flight','gateway stay','package'],'status':'READY' if any(x['eligible'] for x in candidates) else 'VISA_EVIDENCE_REQUIRED'})
    return {'parallel':True,'enabled_groups':enabled,'gateway_priority':[c for c,_ in GATEWAY_PRIORITY],'gateway_candidates':candidates,'ranking':'total_real_cost','sandbox_mock_economic_comparison':False}

@app.get('/api/health')
async def health():
    cache='memory'
    if http.redis:
        try:
            if await http.redis.ping():cache='redis'
        except Exception:pass
    return {'status':'ok','mode':'DEMO_FIRST','read_only':True,'database':'postgresql' if getattr(app.state,'database',False) else 'not_configured_or_unavailable','cache':cache}

@app.get('/api/providers')
async def providers():
    return {'message':'DEMO-FIRST: production-тарифы не подключены. Официальные demo/sandbox отделены от реальных цен.','providers':provider_registry()}

@app.get('/api/public-prices')
async def public_prices():
    return json.loads((Path(__file__).resolve().parents[2]/'data/public_price_observations.json').read_text(encoding='utf-8'))

@app.post('/api/validation/search')
async def test_provider_search(request:ValidationSearch):
    return await validation_search(request)

@app.get('/api/validation/providers')
async def validation_providers():
    return json.loads((Path(__file__).resolve().parents[2]/'data/provider_validation.json').read_text(encoding='utf-8'))

@app.post('/api/search')
async def real_search(request:SearchRequest):
    # Only genuinely connected sources are queried here (see live_search.py):
    # an official public demo needing no personal key, plus any sandbox whose
    # own credentials the operator has put in backend/.env. This route never
    # fills results with mock/fixture offers, and pricing stays DEMO/SANDBOX-
    # labeled (never REAL), so it can never feed the savings calculation.
    f=request.filters
    for key in ('earliest','latest'):
        if key in f:
            try:date.fromisoformat(str(f[key]))
            except ValueError:raise HTTPException(422,'Invalid date')
    live=await gather_live_offers(f,request.party,request.source_settings)
    offers=live['offers'];attempted=live['attempted']
    connected_used=[a['provider'] for a in attempted if a.get('used') and a.get('count',0)>0]
    if offers:
        message=f'Показаны {len(offers)} предложений от подключённых demo/sandbox источников ({", ".join(connected_used)}). Это не production-цены: доступность, визовые условия и итоговая стоимость для семьи не подтверждены.'
    else:
        message='Подтверждённых предложений нет. Проверьте статус источников ниже — часть из них заработает сразу после того, как вы добавите собственные ключи в backend/.env.'
    result={'search_id':str(uuid.uuid4()),'mode':'LIVE','offers':[o.model_dump(mode='json') for o in offers],'count':len(offers),
        'connected':connected_used,'attempted':attempted,
        'message':message,
        'economic_validation':{'comparable_real_offers':0,'savings':None},'providers':provider_registry(),
        'source_settings':request.source_settings.model_dump(),'orchestration':source_orchestration(request)}
    try:storage.save_audit(result['search_id'],'LIVE',{'count':len(offers),'reason':'connected_sources' if offers else 'no_verified_real_inventory'})
    except Exception:pass
    return result

@app.post('/api/flexible-dates')
async def dates(window:SearchWindow):
    try:scenarios=list(flexible_dates(window))
    except ValueError as exc:raise HTTPException(422,str(exc))
    return {'count':len(scenarios),'scenarios':[{**s,'hotel_intervals':occupancy_intervals(window,s)} for s in scenarios[:100]],'truncated':len(scenarios)>100}

class VisaRequest(BaseModel):
    schengen:bool=False
    citizenship:str='RU'
    passport:str='ordinary'
    allow_airside:bool=False
    country:str=Field(min_length=2,max_length=2)
    role:str='gateway'
    arrival:date
    departure:date

@app.post('/api/visa/check')
async def visa_check(request:VisaRequest):
    # No caller-supplied evidence is trusted; licensed/imported verified rules are needed.
    p=VisaProfile(citizenship=request.citizenship,passport=request.passport,schengen=request.schengen,allow_airside_schengen=request.allow_airside)
    return asdict(VisaRuleEngine().assess(p,[Visit(request.country,request.arrival,request.departure,role=request.role)]))

@app.get('/api/weather')
async def weather(latitude:float=Query(ge=-90,le=90),longitude:float=Query(ge=-180,le=180)):
    try:
        r=await http.request('open-meteo','GET','https://api.open-meteo.com/v1/forecast',params={'latitude':latitude,'longitude':longitude,'daily':'temperature_2m_max,temperature_2m_min,precipitation_sum','timezone':'UTC','forecast_days':7},ttl=1800)
        return {'kind':'FORECAST','source':'Open-Meteo','source_url':'https://open-meteo.com/','fetched_at':r['fetched_at'],'climate_score':None,'forecast_score':None,'weather_confidence':None,**r['response']}
    except Exception:raise HTTPException(502,'Public forecast unavailable; no mock substitution')

@app.get('/api/fx')
async def fx():
    try:return await cbr_reference_rates()
    except Exception:raise HTTPException(502,'Reference FX unavailable; no guessed rate')

@app.get('/api/sandbox/travelgate')
async def travelgate():
    try:
        offers=await TravelgateDemo().search({})
        return {'access_status':'DEMO','pricing_reality':'SYNTHETIC','bookable':False,'offers':offers,'fallback':False}
    except Exception as exc:
        return {'access_status':'MOCK','upstream_access_status':'DEMO','pricing_reality':'SYNTHETIC','bookable':False,'offers':await MockProvider().search({'kind':'HOTEL'}),'fallback':True,'reason':type(exc).__name__+': '+str(exc)[:250]}

@app.get('/api/sandbox/dida-content')
async def dida_content():
    try:
        r=await DidaTest().countries()
        return {'access_status':'SANDBOX','pricing_reality':'UNKNOWN','bookable':False,'fetched_at':r['fetched_at'],'countries':r['response'].get('data',[]),'note':'Content only. Shared PriceSearch account retired.'}
    except Exception:raise HTTPException(502,'Dida test content unavailable')
