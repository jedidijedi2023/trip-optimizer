from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from backend.models.domain import CostLine, Money, Access, Reality


def convert(money: Money, rub_per_unit: Decimal, source: str, timestamp: datetime) -> Money:
    if rub_per_unit <= 0 or timestamp.tzinfo is None: raise ValueError('Invalid FX evidence')
    return money.model_copy(update={'converted_amount':(money.original_amount*rub_per_unit).quantize(Decimal('.01'),rounding=ROUND_HALF_UP), 'fx_source':source,'fx_timestamp':timestamp})


def total_cost(lines:list[CostLine]) -> Decimal:
    ids=[line.id for line in lines]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate cost component')
    for line in lines:
        if line.included_in and (line.included_in not in ids or line.included_in == line.id): raise ValueError('Missing parent package')
        if line.included_in and next(x for x in lines if x.id==line.included_in).included_in: raise ValueError('Nested inclusion unsupported')
    total=Decimal('0')
    for line in lines:
        if line.included_in: continue
        m=line.money
        if m.original_currency=='RUB': total+=m.original_amount
        elif m.converted_amount is None or not m.fx_source or m.fx_timestamp is None: raise ValueError('Missing FX evidence')
        else: total+=m.converted_amount
    return total.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)


def economically_comparable(lines:list[CostLine], *, complete:bool, now:datetime|None=None) -> bool:
    now=now or datetime.now(timezone.utc)
    if not complete or not lines: return False
    for line in lines:
        p=line.provenance
        if p.access_status!=Access.LIVE or p.pricing_reality!=Reality.REAL or p.bookable is not True: return False
        if p.expires_at is None or p.fetched_at>now or p.expires_at<=now: return False
        m=line.money
        if m.original_currency!='RUB' and (m.fx_timestamp is None or m.fx_timestamp>now or now-m.fx_timestamp>timedelta(days=2)): return False
    try: total_cost(lines)
    except ValueError: return False
    return True


def real_savings(candidate:list[CostLine], baseline:list[CostLine], *, candidate_key:str, baseline_key:str, complete:bool) -> Decimal|None:
    if candidate_key!=baseline_key or not economically_comparable(candidate,complete=complete) or not economically_comparable(baseline,complete=complete): return None
    return total_cost(baseline)-total_cost(candidate)
