import math
import re
import unicodedata
from difflib import SequenceMatcher
from backend.models.domain import HotelEntity


def normalize_name(name):
    return ' '.join(re.sub(r'[^\w\s]',' ',unicodedata.normalize('NFKC',name).casefold()).split())


def distance_m(a,b):
    lat1,lat2=map(math.radians,(a.latitude,b.latitude))
    dlat=lat2-lat1;dlon=math.radians(b.longitude-a.longitude)
    return 6371000*2*math.asin(math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2))


def match_hotels(a:HotelEntity,b:HotelEntity):
    if a.country!=b.country: return {'confidence':0,'auto_merge':False,'method':'country conflict'}
    if a.giata_id and b.giata_id:
        same=a.giata_id==b.giata_id
        return {'confidence':1 if same else 0,'auto_merge':same,'method':'GIATA'}
    if a.google_place_id and b.google_place_id:
        same=a.google_place_id==b.google_place_id
        return {'confidence':.99 if same else 0,'auto_merge':same,'method':'Google Place'}
    similarity=SequenceMatcher(None,normalize_name(a.name),normalize_name(b.name)).ratio()
    if all(v is not None for v in (a.latitude,a.longitude,b.latitude,b.longitude)):
        distance=distance_m(a,b)
        if distance<80 and similarity>.94: return {'confidence':.96,'auto_merge':True,'method':'coordinates + name'}
        if distance>1000: return {'confidence':0,'auto_merge':False,'method':'coordinate conflict'}
    if a.address and b.address and normalize_name(a.address)==normalize_name(b.address) and similarity>.96:
        return {'confidence':.95,'auto_merge':True,'method':'address + name'}
    return {'confidence':round(similarity*.79,3),'auto_merge':False,'method':'fuzzy — manual review'}
