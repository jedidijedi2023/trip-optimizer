import unittest
from unittest.mock import patch,AsyncMock
import httpx
from backend.providers.http import SafeHTTP

class HttpTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_429_then_cache_success(self):
        attempts=[]
        def handler(request):
            attempts.append(request)
            if len(attempts)==1:return httpx.Response(429,headers={'Retry-After':'0'})
            return httpx.Response(200,json={'daily':[]})
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
        with patch('backend.providers.http.httpx.AsyncClient',return_value=client),patch('backend.providers.http.asyncio.sleep',new=AsyncMock()):
            h=SafeHTTP();h.redis=None
            a=await h.request('test','GET','https://api.open-meteo.com/v1/forecast',params={'latitude':0})
            b=await h.request('test','GET','https://api.open-meteo.com/v1/forecast',params={'latitude':0})
        self.assertEqual(len(attempts),2);self.assertEqual(a,b);self.assertIn('expires_at',b)

    async def test_different_auth_scopes_not_same_cache(self):
        attempts=[]
        def handler(request):
            attempts.append(request);return httpx.Response(200,json={'ok':True})
        transport=httpx.MockTransport(handler)
        real_client=httpx.AsyncClient
        with patch('backend.providers.http.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=transport)),patch('backend.providers.http.asyncio.sleep',new=AsyncMock()):
            h=SafeHTTP();h.redis=None
            a=await h.request('test','GET','https://api.open-meteo.com/v1/forecast',headers={'Authorization':'test-a'})
            b=await h.request('test','GET','https://api.open-meteo.com/v1/forecast',headers={'Authorization':'test-b'})
        self.assertNotEqual(a['query_hash'],b['query_hash']);self.assertEqual(len(attempts),2)
