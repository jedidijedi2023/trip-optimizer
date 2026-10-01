from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Leg:
    id:str
    origin:str
    destination:str
    departure:datetime
    arrival:datetime
    traveller_ids:tuple[str,...]
    mode:str='airplane'
    separate_ticket:bool=False
    bag_recheck:bool=False
    airport_change:bool=False
    overnight:bool=False
    weather_sensitive:bool=False
    cost:Decimal=Decimal('0')


def recommended_buffer(*, minimum=12, children=False, bag_recheck=False, airport_change=False, international_self_transfer=False):
    return max(12,minimum)+(6 if children else 0)+(4 if bag_recheck else 0)+(6 if airport_change else 0)+(6 if international_self_transfer else 0)


def validate_timeline(legs:list[Leg], children:bool=False, minimum_buffer=12):
    if len({l.id for l in legs})!=len(legs): raise ValueError('Duplicate leg')
    supported={'airplane','train','bus','ferry','private_transfer'}
    for leg in legs:
        if leg.mode not in supported or not leg.traveller_ids or len(set(leg.traveller_ids))!=len(leg.traveller_ids): raise ValueError('Invalid leg')
        if leg.departure.tzinfo is None or leg.arrival.tzinfo is None or leg.arrival<=leg.departure: raise ValueError('Invalid aware timestamps')
    for traveller in {t for leg in legs for t in leg.traveller_ids}:
        path=sorted((l for l in legs if traveller in l.traveller_ids),key=lambda l:l.departure)
        for a,b in zip(path,path[1:]):
            if a.destination!=b.origin: raise ValueError('Missing transfer leg')
            hours=(b.departure-a.arrival).total_seconds()/3600
            buffer=recommended_buffer(minimum=minimum_buffer,children=children,bag_recheck=b.bag_recheck,airport_change=b.airport_change,international_self_transfer=b.separate_ticket) if b.separate_ticket else 0
            if hours<buffer: raise ValueError('Overlap or insufficient connection buffer')
    return sorted(legs,key=lambda l:l.departure)


def connection_risk(legs:list[Leg],children=False,visa_unknown=False):
    risk=0
    for leg in legs:
        risk+=15*leg.separate_ticket+10*leg.bag_recheck+18*leg.airport_change+8*leg.overnight+12*(leg.mode=='ferry')+10*leg.weather_sensitive
    return min(100,risk+8*children+25*visa_unknown)


def booking_risk(*,manual=True,nationality_unknown=True,payment_unknown=True,visa_unknown=True,separate_bookings=False,nonrefundable=False,fx_exposure=False,reliability=0.5):
    score=round(15*manual+15*nationality_unknown+15*payment_unknown+20*visa_unknown+10*separate_bookings+8*nonrefundable+7*fx_exposure+10*(1-reliability))
    return {'score':min(100,score),'level':'HIGH' if score>=60 else 'MEDIUM' if score>=30 else 'LOW'}
