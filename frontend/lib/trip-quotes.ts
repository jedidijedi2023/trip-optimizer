import {aviasalesLink,passengerCounts} from './purchase-links';
import type {Offer,Party,Filters} from './search';
export type PackageEvidence={operatorName:string;operatorCountry:string;hotel:string;room:string;meal:string;includesFlightHotel:boolean;purchaseConditionsChecked:boolean};
export type Quote={amount:number;sourceUrl:string;description:string;observedAt:string;confirmed:boolean;access_status:'DEEPLINK';pricing_reality:'REAL'|'LIMITED_REAL';bookable:'unknown';evidence:'USER_REPORTED'|'PUBLIC_PAGE_OBSERVED';queryKey:string;packageEvidence?:PackageEvidence;currency?:'RUB'};
export type QuoteRow={id:string;label:string;queryKey:string};
export function safeSourceUrl(s:string){try{const u=new URL(s);return u.protocol==='https:'&&!u.username&&!u.password&&u.hostname.includes('.')&&!['localhost','127.0.0.1'].includes(u.hostname);}catch{return false;}}
export function quoteValid(q:Quote|undefined,key:string){
 if(!q||q.queryKey!==key||q.confirmed!==true||q.access_status!=='DEEPLINK'||q.pricing_reality!=='REAL'||q.evidence!=='USER_REPORTED'||!Number.isFinite(q.amount)||q.amount<0||!safeSourceUrl(q.sourceUrl)||typeof q.description!=='string'||!q.description.trim()||!Number.isFinite(Date.parse(q.observedAt)))return false;
 if(q.currency!==undefined&&q.currency!=='RUB')return false;
 let isPackage=false;try{isPackage=JSON.parse(key).type==='package';}catch{}
 const p=q.packageEvidence;
 return !isPackage||!!p&&[p.operatorName,p.operatorCountry,p.hotel,p.room,p.meal].every(s=>typeof s==='string'&&s.trim().length>0)&&p.includesFlightHotel===true&&p.purchaseConditionsChecked===true&&q.amount>0;
}
export function quoteTotal(rows:QuoteRow[],quotes:Record<string,Quote>){
 const missing=rows.filter(r=>!quoteValid(quotes[r.id],r.queryKey));
 const total=rows.reduce((sum,r)=>sum+(quoteIncluded(quotes[r.id],r.queryKey)?quotes[r.id].amount:0),0);
 return {total,missing:missing.map(r=>r.label),complete:rows.length>0&&missing.length===0};
}
export function observationValid(q:Quote|undefined,key:string){
 if(!q||q.queryKey!==key||q.confirmed!==false||q.evidence!=='PUBLIC_PAGE_OBSERVED'||q.access_status!=='DEEPLINK'||q.pricing_reality!=='LIMITED_REAL'||q.currency!=='RUB'||!Number.isFinite(q.amount)||q.amount<=0||typeof q.description!=='string'||!q.description.trim()||!safeSourceUrl(q.sourceUrl)||!Number.isFinite(Date.parse(q.observedAt)))return false;
 const ageMs=Date.now()-Date.parse(q.observedAt);if(ageMs<0||ageMs>12*3600000)return false;
 try{const p=JSON.parse(key);if(!['flight','positioning'].includes(p.type))return false;const b=new URL(q.sourceUrl);
  if(b.hostname==='www.aviasales.ru'){const expected=aviasalesLink(p.from,p.to,p.out,p.back,p.adults,p.children).url;return !!expected&&b.pathname===new URL(expected).pathname;}
  if(b.hostname!=='www.kupibilet.ru'||b.pathname!=='/search'&&!b.pathname.startsWith('/mbooking/step0/'))return false;
  const counts=passengerCounts(p.adults,p.children),ages=p.children.filter((a:number)=>a>=2&&a<12);
  const route=(a:string,d:string,z:string)=>new RegExp(`^(?:iatax|airport):${a}_${d}_date_${d}_(?:iatax|airport):${z}$`);
  return b.searchParams.get('adult')===String(counts.adults)&&b.searchParams.get('child')===String(counts.children)&&b.searchParams.get('infant')===String(counts.infants)&&JSON.stringify(JSON.parse(b.searchParams.get('childrenAges')||'null'))===JSON.stringify(ages)&&route(p.from,p.out,p.to).test(b.searchParams.get('route[0]')||'')&&route(p.to,p.back,p.from).test(b.searchParams.get('route[1]')||'');
 }catch{return false;}
}
export function quoteIncluded(q:Quote|undefined,key:string){return quoteValid(q,key)||observationValid(q,key);}
export type TripCalculation={offerKey:string;rows:QuoteRow[];quotes:Record<string,Quote>;parametersValid:boolean;departure:string;returns:string[];from:string;to:string};
export function tripStorageKey(offer:Offer,party:Party,filters:Filters){return 'gto-trip-quotes-v3:'+offer.id+':'+JSON.stringify({party:offer.searchParty||party,rooms:offer.searchRooms||filters.rooms});}
export function calculationValid(c:unknown):c is TripCalculation{
 if(!c||typeof c!=='object')return false;const x=c as TripCalculation;
 return typeof x.offerKey==='string'&&Array.isArray(x.rows)&&x.rows.length>0&&x.rows.every(r=>r&&typeof r.id==='string'&&typeof r.label==='string'&&typeof r.queryKey==='string')&&new Set(x.rows.map(r=>r.id)).size===x.rows.length&&!!x.quotes&&typeof x.quotes==='object'&&typeof x.parametersValid==='boolean'&&typeof x.departure==='string'&&Array.isArray(x.returns)&&x.returns.every(s=>typeof s==='string')&&typeof x.from==='string'&&typeof x.to==='string';
}
export function calculationSummary(c:TripCalculation|undefined){
 if(!calculationValid(c))return {total:0,known:0,unknown:0,pending:0,complete:false};
 const counted=c.rows.filter(r=>quoteIncluded(c.quotes[r.id],r.queryKey));
 const pending=counted.filter(r=>observationValid(c.quotes[r.id],r.queryKey)).length;
 const value=quoteTotal(c.rows,c.quotes);
 return {total:value.total,known:counted.length,unknown:c.rows.length-counted.length,pending,complete:value.complete&&c.parametersValid};
}
