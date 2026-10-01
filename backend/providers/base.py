from abc import ABC, abstractmethod
from enum import Enum
from backend.models.domain import NormalizedOffer, Provenance


class Capability(str,Enum):
    FLIGHT='FLIGHT'
    CHARTER='CHARTER'
    PACKAGE='PACKAGE'
    HOTEL='HOTEL'
    TRANSFER='TRANSFER'
    FERRY='FERRY'
    WEATHER='WEATHER'
    VISA='VISA'


class ProviderUnavailable(Exception): pass


class Provider(ABC):
    name:str
    capabilities:set[Capability]
    @abstractmethod
    async def search(self,query:dict)->list[NormalizedOffer]: ...
    async def details(self,offer_id:str)->NormalizedOffer:
        raise ProviderUnavailable('Read-only details not implemented for this provider')
    async def actualize(self,offer_id:str)->NormalizedOffer:
        raise ProviderUnavailable('No current supplier confirmation available')
    async def availability(self,query:dict)->list[NormalizedOffer]:
        return await self.search(query)


class ForeignPackageProvider(Provider):
    capabilities={Capability.PACKAGE}


class RestrictedAdapter(Provider):
    """Explicit integration boundary; no undocumented wire interface."""
    def __init__(self,name,capabilities,status,source_url):
        self.name=name;self.capabilities=set(capabilities);self.access_status=status;self.source_url=source_url
    async def search(self,query):
        raise ProviderUnavailable(f'{self.name}: {self.access_status}; authorized specification/account required')


class DeeplinkProvider(ForeignPackageProvider):
    def __init__(self,name,url): self.name=name;self.url=url
    def link(self): return {'url':self.url,'prefilled':False,'bookable':None,'pricing_reality':'UNKNOWN','access_status':'DEEPLINK'}
    async def search(self,query): return []
