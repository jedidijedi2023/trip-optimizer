from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class Access(str, Enum):
    LIVE='LIVE'
    TRIAL='TRIAL'
    EVALUATION='EVALUATION'
    SANDBOX='SANDBOX'
    DEMO='DEMO'
    DEEPLINK='DEEPLINK'
    MOCK='MOCK'
    REGISTRATION_REQUIRED='REGISTRATION_REQUIRED'
    COMMERCIAL_CONTRACT_REQUIRED='COMMERCIAL_CONTRACT_REQUIRED'


class Reality(str, Enum):
    REAL='REAL'
    LIMITED_REAL='LIMITED_REAL'
    SYNTHETIC='SYNTHETIC'
    UNKNOWN='UNKNOWN'


class SearchSourceSettings(BaseModel):
    """User-controlled search branches. All branches are enabled by default."""
    search_tour_operators: bool = True
    search_russian_operators: bool = True
    search_foreign_operators: bool = True
    allow_foreign_package_positioning: bool = True
    search_wholesalers: bool = True
    search_retail_diy: bool = True
    positioning_max_price: float | None = Field(default=None, ge=0)
    positioning_max_duration_hours: float | None = Field(default=None, ge=0, le=168)
    positioning_overnight_allowed: bool = True
    positioning_self_transfer_allowed: bool = True
    positioning_min_buffer_hours: float = Field(default=12, ge=1, le=168)


class Provenance(BaseModel):
    provider: str
    access_status: Access
    pricing_reality: Reality
    bookable: bool | None = None
    source_url: str
    fetched_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc))
    expires_at: datetime | None = None
    @model_validator(mode='after')
    def non_live_never_bookable(self):
        if self.fetched_at.tzinfo is None or (self.expires_at is not None and self.expires_at.tzinfo is None):
            raise ValueError('Provenance timestamps require time zones')
        if self.access_status != Access.LIVE or self.pricing_reality != Reality.REAL:
            if self.bookable is True:
                raise ValueError('Only verified LIVE / REAL offers can be bookable')
        return self


class Money(BaseModel):
    original_amount: Decimal = Field(ge=0)
    original_currency: str = Field(pattern=r'^[A-Z]{3}$')
    converted_amount: Decimal | None = Field(default=None, ge=0)
    fx_source: str | None = None
    fx_timestamp: datetime | None = None


class CostLine(BaseModel):
    id: str
    category: str
    money: Money
    mandatory: bool = True
    included_in: str | None = None
    provenance: Provenance


class FlightSegment(BaseModel):
    origin: str
    destination: str
    departure: datetime
    arrival: datetime
    airline: str | None = None
    flight_number: str | None = None
    charter: bool | None = None
    block_seat: bool | None = None
    quota: int | None = None
    available_seats: int | None = None
    baggage_kg: float | None = None
    cabin: str | None = None
    confirmation_status: str = 'UNKNOWN'
    @model_validator(mode='after')
    def aware_chronology(self):
        if self.departure.tzinfo is None or self.arrival.tzinfo is None or self.arrival <= self.departure:
            raise ValueError('Flight times must be timezone-aware and chronological')
        return self


class HotelEntity(BaseModel):
    canonical_id: str
    name: str
    country: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    giata_id: str | None = None
    google_place_id: str | None = None
    provider_ids: dict[str,str] = Field(default_factory=dict)
    mapping_confidence: float = Field(default=0,ge=0,le=1)


class MarketRestrictions(BaseModel):
    seller_country: str | None = None
    market: str | None = None
    allowed_nationalities: list[str] | None = None
    residency_requirement: str | None = None
    payment_card_country_requirement: str | None = None
    billing_address_requirement: str | None = None
    foreign_guest_surcharge: Money | None = None
    passport_requirement: str | None = None
    booking_restriction: str | None = None
    status: Literal['BOOKABLE','LIKELY_BOOKABLE','MANUAL_CONFIRMATION_REQUIRED','NOT_BOOKABLE']='MANUAL_CONFIRMATION_REQUIRED'


class NormalizedOffer(BaseModel):
    id: str
    kind: Literal['FLIGHT','HOTEL','PACKAGE','CHARTER','TRANSFER','FERRY']
    provenance: Provenance
    price: Money
    flights: list[FlightSegment] = Field(default_factory=list)
    hotel: HotelEntity | None = None
    room: str | None = None
    meal: str | None = None
    occupancy: list[dict] = Field(default_factory=list)
    cancellation: dict | None = None
    payment_terms: str | None = None
    restrictions: MarketRestrictions = Field(default_factory=MarketRestrictions)
    mandatory_costs_complete: bool = False
    taxes: Money | None = None
    raw_reference: str | None = None


class TravellerGroup(BaseModel):
    name: str
    traveller_ids: list[str]
    min_nights: int = Field(ge=1,le=60)
    max_nights: int = Field(ge=1,le=60)
    @model_validator(mode='after')
    def nights_valid(self):
        if self.max_nights < self.min_nights: raise ValueError('Invalid night interval')
        return self


class Traveller(BaseModel):
    id: str
    age: int = Field(ge=0,le=110)


class SearchWindow(BaseModel):
    earliest: date
    latest_departure: date
    latest_return: date
    travellers: list[Traveller]
    groups: list[TravellerGroup]
    @model_validator(mode='after')
    def valid_window_and_groups(self):
        if not self.earliest <= self.latest_departure <= self.latest_return: raise ValueError('Invalid date window')
        if (self.latest_return-self.earliest).days>180: raise ValueError('Maximum window is 180 days')
        ids=[t.id for t in self.travellers]
        if len({g.name for g in self.groups})!=len(self.groups): raise ValueError('Group names must be unique')
        assigned=[i for g in self.groups for i in g.traveller_ids]
        if len(set(ids))!=len(ids) or sorted(assigned)!=sorted(ids): raise ValueError('Each traveller belongs to exactly one group')
        ages={t.id:t.age for t in self.travellers}
        if not self.groups or any(not any(ages[i]>=18 for i in g.traveller_ids) for g in self.groups): raise ValueError('Every group requires an adult')
        return self
