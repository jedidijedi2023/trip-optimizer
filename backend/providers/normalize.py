from datetime import datetime
from decimal import Decimal
from backend.models.domain import NormalizedOffer, Provenance, Money, HotelEntity, FlightSegment, Access, Reality


def hotelx_offers(response:dict,provenance:Provenance):
    if response.get('errors'):raise ValueError('HotelX GraphQL errors')
    search=(response.get('data') or {}).get('hotelX',{}).get('search') or {}
    # Documented supplier no-options response is a successful empty search, not an outage.
    warnings=search.get('warnings') or []
    if (search.get('errors') and all(e.get('code')=='ALL_PROCESSES_FAILED' for e in search['errors'])
        and warnings and all(w.get('code')=='11204' for w in warnings)):
        return []
    if search.get('errors'):raise ValueError('HotelX supplier errors: '+str(search['errors'])[:300])
    output=[]
    for o in search.get('options') or []:
        price=o.get('price') or {}
        amount=price.get('gross') if price.get('gross') is not None else price.get('net')
        if amount is None or not price.get('currency'):continue
        code=str(o['hotelCode'])
        output.append(NormalizedOffer(id=o['id'],kind='HOTEL',provenance=provenance,
            price=Money(original_amount=Decimal(str(amount)),original_currency=price['currency']),
            hotel=HotelEntity(canonical_id='travelgate:'+code,name=o.get('hotelName') or code,country='UNKNOWN',provider_ids={'travelgate':code}),
            room=' / '.join(r.get('description','') for r in o.get('rooms',[])),meal=o.get('boardCode'),
            occupancy=o.get('occupancies') or [],cancellation=o.get('cancelPolicy'),payment_terms=o.get('paymentType')))
    return output


def duffel_offers(response:dict,provenance:Provenance):
    output=[]
    for o in response.get('data',{}).get('offers',[]):
        if o.get('live_mode') is True:raise ValueError('Live Duffel response rejected in DEMO-FIRST')
        flights=[]
        for sl in o.get('slices',[]):
            for seg in sl.get('segments',[]):
                dep=seg.get('departing_at');arr=seg.get('arriving_at')
                # Duffel airport local timestamps need IANA zone localization when no offset is supplied.
                from zoneinfo import ZoneInfo
                def local(value,airport):
                    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
                    if dt.tzinfo is None:dt=dt.replace(tzinfo=ZoneInfo(airport['time_zone']))
                    return dt
                flights.append(FlightSegment(origin=seg['origin']['iata_code'],destination=seg['destination']['iata_code'],
                    departure=local(dep,seg['origin']),arrival=local(arr,seg['destination']),
                    airline=seg.get('operating_carrier',{}).get('iata_code'),flight_number=seg.get('operating_carrier_flight_number')))
        output.append(NormalizedOffer(id=o['id'],kind='FLIGHT',provenance=provenance,price=Money(original_amount=o['total_amount'],original_currency=o['total_currency']),flights=flights,cancellation=o.get('conditions'),raw_reference=o['id']))
    return output


def normalized_package(record:dict,provenance:Provenance):
    """Internal normalized contract; not a fabricated external supplier schema."""
    return NormalizedOffer(id=record['id'],kind='PACKAGE',provenance=provenance,
        price=Money.model_validate(record['price']),hotel=HotelEntity.model_validate(record['hotel']),
        flights=[FlightSegment.model_validate(x) for x in record.get('flights',[])],meal=record.get('meal'),
        room=record.get('room'),occupancy=record.get('occupancy',[]),cancellation=record.get('cancellation'),
        mandatory_costs_complete=record.get('mandatory_costs_complete',False))
