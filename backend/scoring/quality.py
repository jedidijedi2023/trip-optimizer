from dataclasses import dataclass


@dataclass
class DestinationQuality:
    climate_score:float|None=None
    forecast_score:float|None=None
    weather_confidence:float=0
    beach_score:float|None=None
    water_score:float|None=None
    family_score:float|None=None
    value_score:float|None=None
    source:str='UNKNOWN'
    kind:str='UNKNOWN'


def total_score(metrics:dict[str,float|None],weights:dict[str,float]):
    if any(v<0 for v in weights.values()) or sum(weights.values())<=0: raise ValueError('Invalid weights')
    if any(metrics.get(k) is None for k,w in weights.items() if w>0): return None
    if any(not 0<=v<=100 for v in metrics.values() if v is not None): raise ValueError('Score outside 0..100')
    return round(sum(metrics[k]*w for k,w in weights.items() if w>0)/sum(weights.values()),2)
