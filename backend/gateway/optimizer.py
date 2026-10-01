from dataclasses import dataclass
from decimal import Decimal
from backend.visa.engine import VisaRuleEngine, VisaProfile, Visit


@dataclass
class GatewayCandidate:
    airport:str
    country:str
    positioning_cost:Decimal
    travel_hours:float
    stay_hours:float
    frequency_per_week:int
    package_available:bool
    payment_confirmed:bool
    nationality_confirmed:bool
    visits:list[Visit]


def eligible_gateways(candidates:list[GatewayCandidate],engine:VisaRuleEngine,profile:VisaProfile,*,max_cost=150000,max_hours=10,max_stay=36,now=None):
    accepted=[]; rejected=[]
    for c in candidates:
        assessment=engine.assess(profile,c.visits,now)
        reasons=[]
        if not assessment.allowed: reasons+=assessment.reasons
        if not c.package_available: reasons.append('Package inventory not confirmed')
        if not c.payment_confirmed or not c.nationality_confirmed: reasons.append('Market/payment restriction unknown')
        if c.positioning_cost>max_cost or c.travel_hours>max_hours or c.stay_hours>max_stay or c.frequency_per_week<1: reasons.append('Gateway limits exceeded')
        if not any(v.role=='gateway' and v.country==c.country for v in c.visits): reasons.append('Missing gateway entry evidence')
        if reasons: rejected.append({'airport':c.airport,'reasons':reasons})
        else: accepted.append(c)
    return sorted(accepted,key=lambda c:(c.positioning_cost,c.travel_hours,-c.frequency_per_week)),rejected
