import unittest
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from backend.visa.engine import VisaRule, VisaRuleEngine, VisaProfile, VisaStatus, Visit

NOW = datetime(2026, 9, 19, tzinfo=timezone.utc)
DAY = date(2026, 10, 10)


def rule(country='TR', **kwargs):
    values = dict(country=country, passport_nationality='RU', passport_type='ordinary', trip_type='tourism',
                  visa_status=VisaStatus.VISA_FREE, source='TEST AUTHORITY — SYNTHETIC', source_url='https://example.org',
                  checked_at=NOW-timedelta(hours=1), expires_at=NOW+timedelta(days=1), valid_from=DAY,
                  valid_to=DAY+timedelta(days=60), max_stay=60, confidence=1, authoritative=True, requirements_verified=True)
    return VisaRule(**(values | kwargs))


class VisaTests(unittest.TestCase):
    def test_schengen_gateway_always_excluded(self):
        for country in ('DE', 'FR', 'IT', 'CY', 'IE'):
            result = VisaRuleEngine([rule(country)]).assess(VisaProfile(), [Visit(country, DAY, DAY, role='gateway')], NOW)
            self.assertFalse(result.allowed)
            self.assertIn('STRICT_NO_SCHENGEN', result.reasons[0])

    def test_airside_toggle_is_not_proof(self):
        p = VisaProfile(allow_airside_schengen=True)
        v = Visit('DE', DAY, DAY, role='transit', airside=True, passport_control=False, airport='FRA', transit_context='single-ticket-LH')
        self.assertFalse(VisaRuleEngine([rule('DE')]).assess(p, [v], NOW).allowed)
        r = rule('DE', airport='FRA', transit_context='single-ticket-LH', airside_without_visa_confirmed=True)
        self.assertTrue(VisaRuleEngine([r]).assess(p, [v], NOW).allowed)
        for change in ({'bag_recheck': True}, {'airport_change': True}, {'overnight': True}, {'passport_control': True}, {'transit_context':'other-ticket'}):
            self.assertFalse(VisaRuleEngine([r]).assess(p, [replace(v, **change)], NOW).allowed)

    def test_unknown_stale_wrong_nationality_or_future_checked(self):
        v = Visit('TR', DAY, DAY)
        for rules in ([], [rule(expires_at=NOW)], [rule(passport_nationality='US')], [rule(checked_at=NOW+timedelta(hours=1))], [rule(requirements_verified=False)]):
            self.assertEqual(VisaRuleEngine(rules).assess(VisaProfile(), [v], NOW).status, VisaStatus.UNKNOWN)

    def test_stay_and_passport(self):
        v = Visit('OM', DAY, DAY+timedelta(days=18))
        self.assertFalse(VisaRuleEngine([rule('OM', max_stay=14)]).assess(VisaProfile(), [v], NOW).allowed)
        self.assertFalse(VisaRuleEngine([rule('OM', passport_validity_days=180)]).assess(VisaProfile(), [v], NOW).allowed)

    def test_multiple_entries_counted(self):
        visits = [Visit('TR', DAY, DAY), Visit('TR', DAY+timedelta(days=10), DAY+timedelta(days=11))]
        self.assertFalse(VisaRuleEngine([rule(max_stay=2)]).assess(VisaProfile(), visits, NOW).allowed)

    def test_destination_and_transit_both_checked(self):
        self.assertFalse(VisaRuleEngine([rule()]).assess(VisaProfile(), [Visit('TR', DAY, DAY), Visit('TH', DAY, DAY)], NOW).allowed)

    def test_conflicting_rules(self):
        self.assertFalse(VisaRuleEngine([rule(), rule(visa_status=VisaStatus.VISA_REQUIRED)]).assess(VisaProfile(), [Visit('TR', DAY, DAY)], NOW).allowed)


if __name__ == '__main__':
    unittest.main()
