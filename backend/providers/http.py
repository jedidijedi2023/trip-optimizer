"""Read/search-only allowlist. No arbitrary upstream URLs or booking methods."""
import asyncio
import hashlib
import json
import os
import time
import re
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
import httpx

ALLOWED={
 ('GET','https://static-apiint.didatravel.com/api/v1/region/countries'),
 ('POST','https://apiint.didatravel.com/api/rate/pricesearch'),
 ('POST','https://api.travelgate.com'),
 ('GET','https://api.test.hotelbeds.com/hotel-api/1.0/status'),
 ('POST','https://api.test.hotelbeds.com/hotel-api/1.0/hotels'),
 ('POST','https://api.duffel.com/air/offer_requests'),
 ('GET','https://api.tourvisor.ru/search/api/v1/departures'),
 ('GET','https://api.tourvisor.ru/search/api/v1/countries'),
 ('GET','https://api.tourvisor.ru/search/api/v1/tours/search'),
 ('POST','https://api-sandbox.ratehawk.com/api/b2b/v3/search/serp/region/'),
 ('GET','https://api.open-meteo.com/v1/forecast'),
 ('GET','https://www.cbr.ru/scripts/XML_daily.asp'),
 ('GET','https://api.travelpayouts.com/aviasales/v3/prices_for_dates'),
}


class SafeHTTP:
    def __init__(self):
        self.cache=OrderedDict();self.next_call={};self.locks={};self.redis=None
        if os.getenv('REDIS_URL'):
            import redis.asyncio as redis
            self.redis=redis.from_url(os.environ['REDIS_URL'],decode_responses=True,socket_connect_timeout=1,socket_timeout=1)

    async def request(self,provider,method,url,*,params=None,json_body=None,headers=None,auth=None,ttl=300):
        tour_result=method=='GET' and re.fullmatch(r'https://api\.tourvisor\.ru/search/api/v1/tours/search/[0-9]+',url)
        if (method,url) not in ALLOWED and not tour_result: raise ValueError('Operation is not in the read/search allowlist')
        if url=='https://api.travelgate.com':
            query=(json_body or {}).get('query','').strip()
            if not query.startswith('query ') or 'mutation' in query.lower(): raise ValueError('Only fixed GraphQL queries are allowed')
            variables=(json_body or {}).get('variables',{})
            if variables.get('settings',{}).get('testMode') is not True or variables.get('settings',{}).get('client')!='client_demo': raise ValueError('HotelX demo only')
            if variables.get('filterSearch',{}).get('access',{}).get('includes')!=['2']:
                raise ValueError('Only HOTELTEST access 2 is allowed')
            hotels=variables.get('criteriaSearch',{}).get('hotels')
            if hotels!=['ES284122','BR1518']:
                raise ValueError('Only documented HOTELTEST demo hotels are allowed')
        scope=hashlib.sha256(json.dumps([headers,auth],sort_keys=True,default=str).encode()).hexdigest()
        digest=hashlib.sha256(json.dumps([method,url,params,json_body,scope],sort_keys=True,default=str).encode()).hexdigest()
        key=f'gto:{provider}:{digest}';now=datetime.now(timezone.utc)
        cached=self.cache.get(key)
        if cached and datetime.fromisoformat(cached['expires_at'])>now: return cached
        if self.redis:
            try:
                raw=await self.redis.get(key)
                if raw:return json.loads(raw)
            except Exception: pass  # Local demo remains usable without Redis; health reports fallback.
        lock=self.locks.setdefault(provider,asyncio.Lock())
        async with lock:
            # Conservative 1 QPS per provider per process; distributed rate limiting is a deployment task.
            async with httpx.AsyncClient(timeout=30,follow_redirects=False) as client:
                for attempt in range(3):
                    await asyncio.sleep(max(0,self.next_call.get(provider,0)-time.monotonic()))
                    self.next_call[provider]=time.monotonic()+1
                    try:
                        r=await client.request(method,url,params=params,json=json_body,headers=headers,auth=auth)
                    except (httpx.TimeoutException,httpx.NetworkError):
                        if attempt==2:raise
                        await asyncio.sleep(2**attempt);continue
                    if (r.status_code==429 or r.status_code>=500) and attempt<2:
                        retry=r.headers.get('Retry-After','')
                        await asyncio.sleep(min(30,float(retry)) if retry.isdigit() else 2**attempt);continue
                    r.raise_for_status()
                    data=r.json() if 'json' in r.headers.get('content-type','') else r.text
                    fetched=datetime.now(timezone.utc)
                    result={'provider':provider,'query_hash':digest,'response':data,'fetched_at':fetched.isoformat(),'expires_at':(fetched+timedelta(seconds=ttl)).isoformat(),'http_status':r.status_code}
                    # Supplier errors are not successful cached responses.
                    if isinstance(data,dict) and (data.get('errors') or data.get('Error')):return result
                    self.cache[key]=result
                    while len(self.cache)>128:self.cache.popitem(last=False)
                    if self.redis:
                        try:await self.redis.setex(key,ttl,json.dumps(result))
                        except Exception:pass
                    return result
        raise RuntimeError('Request exhausted retries')


http=SafeHTTP()
