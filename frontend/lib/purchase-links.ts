import type {Party} from './search';

export const destinationAirports:Record<string,string>={EG:'HRG',TR:'AYT',TH:'HKT',MV:'MLE',OM:'SLL',AE:'DXB',VN:'PQC',LK:'CMB',ID:'DPS',SC:'SEZ',MU:'MRU',TZ:'ZNZ',MY:'LGK',PH:'MPH',IN:'GOI',QA:'DOH',ES:'PMI'};
export type SearchGroup={name:string;adults:number;children:number[];back:string};
export function flightGroups(p:Party,returns:string[]):SearchGroup[]{
 return p.split?p.groups.map((g,i)=>({name:g.name,adults:g.adults,children:g.children.map(j=>p.children[j]),back:returns[i]||returns[0]})):[{name:'Вся семья',adults:p.adults,children:[...p.children],back:returns[0]}];
}
export function validDate(s:string){return /^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s;}
export function datesError(out:string,back:string,hotel=false,today=new Date().toLocaleDateString('sv-SE')){
 if(!validDate(out)||out<today||(!back&&hotel)||back&&(!validDate(back)||back<out||hotel&&back===out))return 'Укажите будущий вылет/заезд и корректное возвращение/выезд.';
}
export function passengerCounts(adults:number,ages:number[]){return {adults:adults+ages.filter(a=>a>=12).length,children:ages.filter(a=>a>=2&&a<12).length,infants:ages.filter(a=>a<2).length};}
// Official format: https://support.travelpayouts.com/hc/ru/articles/5711895629714
export function aviasalesLink(from:string,to:string,out:string,back:string,adults:number,ages:number[],today=new Date().toLocaleDateString('sv-SE')):{url?:string;formUrl?:string;error?:string}{
 if(!/^[A-Z]{3}$/.test(from)||!/^[A-Z]{3}$/.test(to)||from===to)return {error:'Укажите разные трёхбуквенные IATA-коды.'};
 const error=datesError(out,back,false,today);if(error)return {error};
 const next=(s:string,base:string)=>{let d=base.slice(0,4)+s.slice(4);if(d<base)d=String(Number(base.slice(0,4))+1)+s.slice(4);return d===s;};
 if(!next(out,today)||back&&!next(back,out))return {error:'Aviasales не передаёт год в этой ссылке: доступны даты ближайшего годового цикла.'};
 const {adults:a,children:c,infants:i}=passengerCounts(adults,ages);
 if(!Number.isInteger(adults)||adults<1||ages.some(x=>!Number.isInteger(x)||x<0||x>17)||a>9||c>9||i>9||i>adults)return {error:'Разделите пассажиров на группы: этот состав не поддерживается ссылкой.'};
 const dm=(s:string)=>s.slice(8,10)+s.slice(5,7);
 const passengers=String(a)+(c||i?String(c):'')+(i?String(i):'');
 const params=from+dm(out)+to+(back?dm(back):'')+passengers;
 return {url:'https://www.aviasales.ru/search/'+params,formUrl:'https://www.aviasales.ru/?params='+params};
}
// Public search URL observed on Kupibilet's own results/booking pages on 2026-09-28.
export function kupibiletLink(from:string,to:string,out:string,back:string,adults:number,ages:number[]){
 if(!/^[A-Z]{3}$/.test(from)||!/^[A-Z]{3}$/.test(to)||from===to)return;
 if(datesError(out,back)||ages.some(a=>!Number.isInteger(a)||a<0||a>17))return;
 const p=passengerCounts(adults,ages),children=ages.filter(a=>a>=2&&a<12);
 if(p.adults<1||p.adults+p.children+p.infants>9)return;
 const u=new URL('https://www.kupibilet.ru/search');
 u.searchParams.set('route[0]',`iatax:${from}_${out}_date_${out}_iatax:${to}`);
 if(back)u.searchParams.set('route[1]',`iatax:${to}_${back}_date_${back}_iatax:${from}`);
 u.searchParams.set('adult',String(p.adults));u.searchParams.set('child',String(p.children));u.searchParams.set('infant',String(p.infants));u.searchParams.set('childrenAges',JSON.stringify(children));u.searchParams.set('cabinClass','Y');u.searchParams.set('v','2');
 return u.toString();
}
export function bookingLink(place:string,out:string,back:string,adults:number,ages:number[],rooms:number){
 const u=new URL('https://www.booking.com/searchresults.html');
 Object.entries({ss:place,checkin:out,checkout:back,group_adults:String(adults),group_children:String(ages.length),no_rooms:String(rooms),selected_currency:'RUB'}).forEach(([k,v])=>u.searchParams.set(k,v));
 ages.forEach(a=>u.searchParams.append('age',String(a)));return u.toString();
}
// Published destination pages. Other destinations remain unavailable until mapped, never guessed.
export const ostrovokPlaces:Record<string,string>={'Макади-Бей':'egypt/makadi_bay','Белек':'turkey/belek','Као-Лак':'thailand/khao_lak','Рас-эль-Хайма':'united_arab_emirates/ras_al_khaimah','Анталья':'turkey/antalya'};
export function ostrovokLink(place:string,out:string,back:string,adults:number,ages:number[]){
 const path=ostrovokPlaces[place];if(!path)return;
 const d=(s:string)=>s.slice(8,10)+'.'+s.slice(5,7)+'.'+s.slice(0,4);
 const u=new URL('https://ostrovok.ru/hotel/'+path+'/');
 u.searchParams.set('dates',d(out)+'-'+d(back));u.searchParams.set('guests',String(adults)+(ages.length?'and'+ages.join('.') :''));u.searchParams.set('cur','RUB');u.searchParams.set('price','total');return u.toString();
}
