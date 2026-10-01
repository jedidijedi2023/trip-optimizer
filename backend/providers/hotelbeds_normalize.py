from backend.models.domain import NormalizedOffer, Money, HotelEntity

def hotelbeds_offers(response,provenance):
    offers=[]
    for h in response.get('hotels',{}).get('hotels',[]):
        for room in h.get('rooms',[]):
            for rate in room.get('rates',[]):
                offers.append(NormalizedOffer(id=rate['rateKey'],kind='HOTEL',provenance=provenance,
                    price=Money(original_amount=rate['net'],original_currency=h['currency']),
                    hotel=HotelEntity(canonical_id='hotelbeds:'+str(h['code']),name=h['name'],country='UNKNOWN',provider_ids={'hotelbeds':str(h['code'])}),
                    room=room.get('name'),meal=rate.get('boardCode'),occupancy=[{'rooms':rate.get('rooms'),'adults':rate.get('adults'),'children':rate.get('children')}],
                    cancellation={'penalties':rate.get('cancellationPolicies',[])},payment_terms=rate.get('paymentType')))
    return offers
