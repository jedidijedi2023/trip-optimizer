"""Fail-closed entry assessment. Rules are supplied as dated evidence, never inferred."""
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum


class VisaStatus(str, Enum):
    VISA_FREE = 'VISA_FREE'
    VISA_ON_ARRIVAL = 'VISA_ON_ARRIVAL'
    EVISA = 'EVISA'
    VISA_REQUIRED = 'VISA_REQUIRED'
    TRANSIT_VISA_REQUIRED = 'TRANSIT_VISA_REQUIRED'
    UNKNOWN = 'UNKNOWN'


# Jurisdiction classification, not entry rules. Review this version when membership changes.
SCHENGEN = frozenset('AT BE BG HR CZ DK EE FI FR DE GR HU IS IT LV LI LT LU MT NL NO PL PT RO SK SI ES SE CH'.split())
EU = SCHENGEN - {'IS', 'LI', 'NO', 'CH'} | {'IE', 'CY'}


@dataclass
class VisaProfile:
    citizenship: str = 'RU'
    passport: str = 'ordinary'
    schengen: bool = False
    uk: bool = False
    usa: bool = False
    canada: bool = False
    other_visas: list[str] = field(default_factory=list)
    allow_voa: bool = True
    allow_evisa: bool = True
    allow_new_visa: bool = False
    max_visa_cost: float = 20000
    max_processing_days: int = 7
    passport_expiry: date | None = None
    allow_airside_schengen: bool = False

    @property
    def strict_no_schengen(self):
        return not self.schengen


@dataclass
class Visit:
    country: str
    arrival: date
    departure: date
    trip_type: str = 'tourism'
    role: str = 'destination'
    airport: str | None = None
    airside: bool = False
    bag_recheck: bool = False
    airport_change: bool = False
    passport_control: bool = True
    overnight: bool = False
    separate_tickets: bool = False
    transit_context: str | None = None


@dataclass
class VisaRule:
    country: str
    passport_nationality: str
    passport_type: str
    trip_type: str
    visa_status: VisaStatus
    source: str
    source_url: str
    checked_at: datetime
    expires_at: datetime
    valid_from: date
    valid_to: date
    max_stay: int
    requirements: list[str] = field(default_factory=list)
    confidence: float = 0.0
    authoritative: bool = False
    requirements_verified: bool = False
    passport_validity_days: int = 0
    visa_cost_rub: float = 0
    processing_days: int = 0
    airport: str | None = None
    transit_context: str | None = None
    airside_without_visa_confirmed: bool = False


@dataclass
class Assessment:
    allowed: bool
    status: VisaStatus
    reasons: list[str]
    evidence: list[VisaRule] = field(default_factory=list)


class VisaRuleEngine:
    def __init__(self, rules: list[VisaRule] | None = None):
        self.rules = rules or []

    def assess(self, profile: VisaProfile, visits: list[Visit], now: datetime | None = None) -> Assessment:
        now = now or datetime.now(timezone.utc)
        if not visits:
            return Assessment(False, VisaStatus.UNKNOWN, ['Маршрут не содержит проверяемых участков'])
        evidence = []
        for visit in visits:
            if visit.departure < visit.arrival:
                return Assessment(False, VisaStatus.UNKNOWN, ['Некорректные даты участка'])
            if profile.strict_no_schengen:
                if visit.role == 'gateway' and visit.country in EU | SCHENGEN:
                    return Assessment(False, VisaStatus.VISA_REQUIRED, ['STRICT_NO_SCHENGEN: европейский gateway исключён'])
                if visit.country in SCHENGEN:
                    if not (profile.allow_airside_schengen and visit.role == 'transit' and visit.airside
                            and not visit.bag_recheck and not visit.airport_change and not visit.passport_control
                            and not visit.overnight and visit.transit_context):
                        return Assessment(False, VisaStatus.VISA_REQUIRED, ['STRICT_NO_SCHENGEN: въезд или неподтверждённый транзит'])
            matches = [r for r in self.rules if r.country == visit.country
                       and r.passport_nationality == profile.citizenship and r.passport_type == profile.passport
                       and r.trip_type == visit.trip_type and r.valid_from <= visit.arrival <= visit.departure <= r.valid_to
                       and r.checked_at <= now < r.expires_at and r.authoritative and r.confidence >= .9
                       and r.source_url.startswith('https://') and r.requirements_verified]
            if not matches:
                return Assessment(False, VisaStatus.UNKNOWN, [f'{visit.country}: нет актуального подтверждения правил'])
            if len({r.visa_status for r in matches}) > 1:
                return Assessment(False, VisaStatus.UNKNOWN, [f'{visit.country}: противоречивые источники'])
            rule = max(matches, key=lambda r: r.checked_at)
            if profile.strict_no_schengen and visit.country in SCHENGEN:
                if not (rule.airside_without_visa_confirmed and rule.airport == visit.airport
                        and rule.transit_context == visit.transit_context and rule.visa_status == VisaStatus.VISA_FREE):
                    return Assessment(False, VisaStatus.UNKNOWN, ['Нет официального подтверждения конкретного airside transit'])
            # Count all entries into a country conservatively; a cumulative-days provider can refine this.
            stay = sum((v.departure - v.arrival).days + 1 for v in visits if v.country == visit.country)
            if stay > rule.max_stay:
                return Assessment(False, VisaStatus.VISA_REQUIRED, [f'{visit.country}: превышен срок пребывания'])
            if rule.passport_validity_days and profile.passport_expiry is None:
                return Assessment(False, VisaStatus.UNKNOWN, ['Не указана дата окончания паспорта'])
            if profile.passport_expiry and (profile.passport_expiry - visit.departure).days < rule.passport_validity_days:
                return Assessment(False, VisaStatus.VISA_REQUIRED, ['Недостаточный срок действия паспорта'])
            if rule.visa_status in (VisaStatus.UNKNOWN, VisaStatus.TRANSIT_VISA_REQUIRED):
                return Assessment(False, rule.visa_status, ['Требуется индивидуальная проверка транзита'])
            if rule.visa_status == VisaStatus.VISA_REQUIRED:
                # Applying is a planning option, never proof of an issued visa.
                return Assessment(False, rule.visa_status, ['Требуется подтверждение выданной визы для дат поездки'])
            if rule.visa_status == VisaStatus.EVISA and not profile.allow_evisa:
                return Assessment(False, rule.visa_status, ['eVisa запрещена профилем'])
            if rule.visa_status == VisaStatus.VISA_ON_ARRIVAL and not profile.allow_voa:
                return Assessment(False, rule.visa_status, ['Виза по прибытии запрещена профилем'])
            if rule.visa_cost_rub > profile.max_visa_cost or rule.processing_days > profile.max_processing_days:
                return Assessment(False, rule.visa_status, ['Виза превышает лимит стоимости или срока'])
            evidence.append(rule)
        status = next((r.visa_status for r in evidence if r.visa_status != VisaStatus.VISA_FREE), VisaStatus.VISA_FREE)
        return Assessment(True, status, ['Правила и условия подтверждены для каждого участка'], evidence)
