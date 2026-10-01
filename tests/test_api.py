import unittest
from fastapi.testclient import TestClient
from backend.api.main import app

class APITests(unittest.TestCase):
    def setUp(self):self.client=TestClient(app)
    def test_live_never_returns_mock(self):
        response=self.client.post('/api/search',json={'filters':{'earliest':'2026-09-20','latest':'2026-11-30'},'party':{'adults':2,'children':[5,7,9]}})
        self.assertEqual(response.status_code,200)
        body=response.json()
        # Offers may be empty (no network / no connected sandbox) or non-empty
        # (Travelgate demo / RateHawk sandbox reachable), but never MOCK access
        # and never counted toward savings, whichever it is.
        for o in body['offers']:self.assertNotEqual(o['provenance']['access_status'],'MOCK')
        self.assertEqual(body['economic_validation']['savings'],None)
        self.assertTrue(body['source_settings']['search_tour_operators'])
        self.assertEqual(body['source_settings']['positioning_min_buffer_hours'],12)
        self.assertFalse(body['orchestration']['sandbox_mock_economic_comparison'])
        self.assertIn('attempted',body)
    def test_source_switches_control_parallel_plan(self):
        r=self.client.post('/api/search',json={'filters':{'earliest':'2026-09-20','latest':'2026-11-30'},'source_settings':{'search_tour_operators':False,'search_wholesalers':True,'search_retail_diy':False}})
        self.assertEqual(r.status_code,200)
        groups=[x['group'] for x in r.json()['orchestration']['enabled_groups']]
        self.assertEqual(groups,['WHOLESALERS_B2B'])
    def test_foreign_gateway_plan_is_visa_fail_closed(self):
        r=self.client.post('/api/search',json={'filters':{'earliest':'2026-09-20','latest':'2026-11-30','schengen':False}})
        plan=r.json()['orchestration']
        self.assertEqual(plan['gateway_priority'][:5],['TR','AE','QA','OM','CN'])
        self.assertNotIn('DE',plan['gateway_priority'])
        self.assertTrue(plan['gateway_candidates'])
        self.assertTrue(all(not x['eligible'] for x in plan['gateway_candidates']))
        foreign=next(x for x in plan['enabled_groups'] if x['group']=='FOREIGN_TOUR_OPERATORS')
        self.assertEqual(foreign['status'],'VISA_EVIDENCE_REQUIRED')
    def test_booking_endpoint_absent(self):self.assertEqual(self.client.post('/api/book').status_code,404)
    def test_schengen_excluded(self):
        r=self.client.post('/api/visa/check',json={'country':'DE','arrival':'2026-10-18','departure':'2026-10-19'})
        self.assertFalse(r.json()['allowed']);self.assertIn('STRICT_NO_SCHENGEN',r.json()['reasons'][0])
    def test_unknown_gateway_not_approved(self):
        r=self.client.post('/api/visa/check',json={'country':'AE','arrival':'2026-10-18','departure':'2026-10-19'})
        self.assertEqual(r.json()['status'],'UNKNOWN')
    def test_invalid_dates(self):self.assertEqual(self.client.post('/api/search',json={'filters':{'earliest':'bad'}}).status_code,422)
    def test_all_provider_provenance_fields(self):
        for p in self.client.get('/api/providers').json()['providers']:
            self.assertIn('access_status',p);self.assertIn('pricing_reality',p);self.assertIn('bookable',p)
    def test_public_observations_not_verified_family_quotes(self):
        data=self.client.get('/api/public-prices').json()
        self.assertGreater(len(data['observations']),0)
        for o in data['observations']:
            self.assertEqual(o['pricing_reality'],'LIMITED_REAL');self.assertIsNone(o['bookable'])
