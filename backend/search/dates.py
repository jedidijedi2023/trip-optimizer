from datetime import timedelta
from itertools import product
from backend.models.domain import SearchWindow


def flexible_dates(window:SearchWindow, limit:int=100000):
    """Yield common outbound and independent inbound dates, not separate family trips."""
    combinations=1
    for g in window.groups: combinations*=g.max_nights-g.min_nights+1
    if combinations*((window.latest_departure-window.earliest).days+1)>limit:
        raise ValueError('Search exceeds scenario budget; narrow the window')
    departure=window.earliest
    while departure<=window.latest_departure:
        for nights in product(*(range(g.min_nights,g.max_nights+1) for g in window.groups)):
            returns=[departure+timedelta(days=n) for n in nights]
            if max(returns)<=window.latest_return:
                yield {'departure':departure,'returns':dict(zip((g.name for g in window.groups),returns)), 'nights':nights}
        departure+=timedelta(days=1)


def occupancy_intervals(window:SearchWindow, scenario:dict):
    """All occupants are present initially; departed groups leave subsequent hotel periods."""
    departure=scenario['departure']
    returns=scenario['returns']
    ends=sorted(set(returns.values()))
    output=[]
    for end in ends:
        occupants=[i for group in window.groups if returns[group.name]>departure for i in group.traveller_ids]
        output.append({'check_in':departure,'check_out':end,'traveller_ids':occupants,'nights':(end-departure).days})
        departure=end
    return output
