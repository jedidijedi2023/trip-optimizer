export function isPackageKind(kind:string){return ['russian','foreign','gatewayPackage'].includes(kind);}
export type PackageRequestInput={kind:string;from:string;to:string;country:string;resort:string;out:string;back:string;adults:number;children:number[];meal:string;stars:number;rating:number;operatorCountry:string};
export function packageRequest(p:PackageRequestInput){
 const nights=(Date.parse(p.back)-Date.parse(p.out))/86400000;
 return {schemaVersion:1,product:'package',operatorMarket:p.kind==='russian'?'RUSSIAN':'FOREIGN',operatorCountry:p.operatorCountry,
  departureAirport:p.from,arrivalAirport:p.to,destinationCountry:p.country,resort:p.resort,departureDate:p.out,returnDate:p.back,
  nights:Number.isInteger(nights)&&nights>0?nights:null,dateToleranceDays:0,nightTolerance:0,
  occupancy:[{adults:p.adults,childrenAges:[...p.children]}],numberOfRooms:1,meal:p.meal,minimumStars:p.stars,minimumRating:p.rating,
  requiredComponents:['outbound_flight','return_flight','hotel'],priceBasis:'TOTAL_FOR_ALL_GUESTS_AND_NIGHTS',
  requestOnly:true,price:null,availabilityConfirmed:false};
}
