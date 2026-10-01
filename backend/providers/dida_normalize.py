from backend.models.domain import NormalizedOffer,Money,HotelEntity

def dida_offers(response,provenance):
    """Only accept a validated supplier response, never guess unfamiliar prices."""
    if not isinstance(response,dict):raise ValueError('Dida returned non-JSON response')
    if response.get('Error'):raise ValueError('Dida supplier error')
    if not response.get('Success',False):raise ValueError('Dida response not confirmed successful')
    # Dedicated account mapping is intentionally blocked until an authorized response
    # contract is validated. Content access alone does not validate a price contract.
    raise ValueError('Dida dedicated sandbox price normalization pending test response; use labeled mock')
