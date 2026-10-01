export type Value = string | number | boolean;
export type Filters = Record<string, Value>;
export type Field = {key:string; label:string; type:'number'|'text'|'date'|'check'|'select'; options?:string[]; min?:number; max?:number; note?:string};
export type Section = {name:string; fields:Field[]};
export type SearchSourceSettings={
 search_tour_operators:boolean;search_russian_operators:boolean;search_foreign_operators:boolean;allow_foreign_package_positioning:boolean;
 search_wholesalers:boolean;search_retail_diy:boolean;positioning_max_price:number|null;positioning_max_duration_hours:number|null;
 positioning_overnight_allowed:boolean;positioning_self_transfer_allowed:boolean;positioning_min_buffer_hours:number;
};
export const defaultSearchSourceSettings:SearchSourceSettings={search_tour_operators:true,search_russian_operators:true,search_foreign_operators:true,allow_foreign_package_positioning:true,search_wholesalers:true,search_retail_diy:true,positioning_max_price:null,positioning_max_duration_hours:null,positioning_overnight_allowed:true,positioning_self_transfer_allowed:true,positioning_min_buffer_hours:12};
const n=(key:string,label:string,min=0,max=10000000):Field=>({key,label,type:'number',min,max});
const c=(key:string,label:string):Field=>({key,label,type:'check'});
const s=(key:string,label:string,options:string[]):Field=>({key,label,type:'select',options});
const t=(key:string,label:string):Field=>({key,label,type:'text'});
export const sections:Section[]=[
 {name:'Откуда и когда',fields:[t('origin','Город вылета'),t('airports','Аэропорты через запятую'),n('radius','Соседние аэропорты, км',0,1000),{key:'earliest',label:'Первый вылет',type:'date'},{key:'latestDeparture',label:'Последний вылет',type:'date'},{key:'latest',label:'Вернуться не позже',type:'date'},n('minNights','Минимум ночей',1,60),n('maxNights','Максимум ночей',1,60)]},
 {name:'Документы и визы',fields:[s('citizenship','Гражданство',['RU','AM','KZ','US','OTHER']),s('passport','Тип паспорта',['ordinary','diplomatic']),c('uk','Есть виза Великобритании'),c('usa','Есть виза США'),c('canada','Есть виза Канады'),t('otherVisas','Другие визы: коды стран через запятую'),c('evisa','Разрешить eVisa'),c('voa','Разрешить визу по прибытии'),c('newVisa','Готов оформить новую визу'),n('visaCost','Лимит визовых расходов, ₽'),n('visaDays','Максимум дней оформления',0,180),{key:'passportExpiry',label:'Срок действия паспорта (необязательно)',type:'date'},c('airside','Разрешить безвизовый airside transit через Европу')]},
 {name:'Направления и бюджет',fields:[s('destinationMode','Поиск направления',['Любой пляж','Выбранные страны']),t('destinations','Страны или коды через запятую'),n('budget','Бюджет всей семьи, ₽'),n('perPerson','Максимум на человека, ₽ (0 — без лимита)'),s('currency','Валюта итогового сравнения',['RUB']),s('meal','Питание',['Любое','RO','BB','HB','FB','AI','UAI']),c('countryMeals','Предпочитать AI в Египте/Турции, BB в Азии')]},
 {name:'Отель и семья',fields:[n('stars','Минимум звёзд',1,5),n('rating','Минимум оценки гостей',0,10),n('rooms','Номеров',1,6),c('familyRoom','Семейный номер'),c('connecting','Смежные номера'),c('apartments','Разрешить виллы и апартаменты'),c('firstLine','Только первая линия'),c('privateBeach','Частный пляж'),c('pool','Бассейн'),c('kidsPool','Детский бассейн'),c('kidsClub','Детский клуб'),c('waterpark','Аквапарк')]},
 {name:'Пляж, вода и приливы',fields:[s('sand','Покрытие пляжа',['Любое','Песок','Мелкий песок','Галька','Коралл']),s('entry','Вход в воду',['Любой','Пологий','Обычный','Глубокий']),c('noPontoon','Без понтона'),s('reef','Риф',['Неважно','Нужен','Без рифа']),n('water','Минимальная оценка воды',1,5),n('clarity','Прозрачность воды',1,5),n('colour','Цвет воды',1,5),c('turquoise','Бирюзовая вода'),c('maldives','Вода как на Мальдивах'),s('tides','Чувствительность к отливам',['Любая','LOW','MEDIUM','HIGH']),n('retreat','Максимальный отступ воды, м',0,1000),c('lowTideSwim','Купание во время отлива')]},
 {name:'Погода',fields:[n('sea','Температура моря от, °C',0,40),n('dayMin','Температура днём от, °C',0,50),n('dayMax','Температура днём до, °C',0,50),n('rain','Максимум осадков, мм',0,1000),n('rainyDays','Максимум дождливых дней в месяце',0,31),n('weather','Минимальная оценка погоды',0,100),c('monsoon','Избегать муссонов'),c('typhoon','Избегать сезона тайфунов'),c('hurricane','Избегать сезона ураганов'),n('weatherImportance','Важность погоды',1,5)]},
 {name:'Перелёт',fields:[c('directPreferred','Прямой рейс предпочтителен'),c('direct','Только прямой рейс'),n('stops','Максимум пересадок',0,4),n('baggage','Багаж от, кг',0,40),n('carryOn','Ручная кладь от, кг',0,20),n('flightHours','Максимум часов перелёта',1,72),n('layover','Максимум часов пересадки',0,72),c('overnight','Разрешить ночную пересадку'),c('selfTransfer','Разрешить самостоятельную пересадку'),c('airportChange','Разрешить смену аэропорта')]},
 {name:'Приоритеты сравнения',fields:[n('wWeather','Погода, вес',0,100),n('wBeach','Пляж, вес',0,100),n('wPrice','Цена, вес',0,100),n('wConvenience','Удобство дороги, вес',0,100),n('wHotel','Отель, вес',0,100)]}
];
export const defaults:Filters={origin:'Москва',airports:'SVO,DME,VKO',radius:0,earliest:'2026-09-20',latestDeparture:'2026-11-20',latest:'2026-11-30',minNights:8,maxNights:20,citizenship:'RU',passport:'ordinary',schengen:false,uk:false,usa:false,canada:false,otherVisas:'',evisa:true,voa:true,newVisa:false,visaCost:20000,visaDays:7,passportExpiry:'',airside:false,destinationMode:'Любой пляж',destinations:'',budget:600000,perPerson:0,currency:'RUB',meal:'Любое',countryMeals:true,stars:4,rating:8,rooms:2,familyRoom:false,connecting:false,apartments:true,firstLine:true,privateBeach:false,pool:true,kidsPool:false,kidsClub:false,waterpark:false,sand:'Песок',entry:'Пологий',noPontoon:true,reef:'Неважно',water:4,clarity:1,colour:1,turquoise:false,maldives:false,tides:'Любая',retreat:500,lowTideSwim:false,sea:25,dayMin:25,dayMax:36,rain:250,rainyDays:20,weather:75,monsoon:true,typhoon:true,hurricane:true,weatherImportance:3,directPreferred:true,direct:false,stops:2,baggage:20,carryOn:5,flightHours:20,layover:30,overnight:true,selfTransfer:true,airportChange:false,gateway:true,gatewayCountries:'AUTO',visaCompatible:true,positionPrice:150000,positionHours:10,gatewayStay:36,gatewayOvernight:true,buffer:12,russian:true,foreign:true,diy:true,charter:true,wholesale:true,gatewayPackage:true,wWeather:30,wBeach:25,wPrice:25,wConvenience:10,wHotel:10};
export type Party={adults:number;children:number[];split:boolean;groups:{name:string;adults:number;children:number[];minNights:number;maxNights:number}[]};
export const defaultParty:Party={adults:2,children:[5,7,9],split:false,groups:[{name:'Группа A',adults:1,children:[1,2],minNights:9,maxNights:9},{name:'Группа B',adults:1,children:[0],minNights:18,maxNights:18}]};
export type Offer={searchParty?:Party;searchRooms?:number;id:string;country:string;code:string;resort:string;hotel:string;kind:string;meal:string;departure:string;returns:string[];nights:number[];people:number;price:number;costs:{label:string;amount:number;currency:string;original:number;included?:boolean}[];weather:number;beach:number;water:number;family:number;score:number;sea:number;air:number;stars:number;rating:number;gateway:string;gatewayCountry:string;route:string[];risk:number;bookingRisk:number;buffer:number;visa:string;source:string;sourceUrl:string;savings:number|null;comparisonKey:string;explanation:string;demo:true;available:false;access_status:'MOCK';pricing_reality:'SYNTHETIC';bookable:false;flightHours:number;groupLabels:string[];reasons:string[];operatorName:string;operatorCountry:string;startAirport:string;positioningCost:number;gatewayHotelCost:number;overnightNeeded:boolean;selfTransfer:boolean;visaDecision:'OK'|'CHECK'|'REQUIRED';packagePrice:number;additionalCosts:number;totalRealCost:number};
const destinations=[
 ['EG','Египет','Макади-Бей',.92,88,90,4.3,27,31,'VISA_ON_ARRIVAL'],['TR','Турция','Белек',.97,80,85,4,25,28,'VISA_FREE'],
 ['TH','Таиланд','Као-Лак',1.06,81,94,4.5,29,31,'VISA_FREE'],['MV','Мальдивы','Северный Мале',1.65,87,99,5,29,30,'VISA_ON_ARRIVAL'],
 ['OM','Оман','Салала',1.03,91,91,4.4,27,30,'UNKNOWN'],['AE','ОАЭ','Рас-эль-Хайма',1.04,94,86,4.1,28,32,'UNKNOWN'],
 ['VN','Вьетнам','Фукуок',1.07,79,91,4.2,28,30,'VISA_FREE'],['LK','Шри-Ланка','Тринкомали',.99,78,92,4.4,28,30,'EVISA'],
 ['ID','Индонезия','Нуса-Дуа',1.22,81,88,4,28,30,'VISA_ON_ARRIVAL'],['SC','Сейшелы','Праслин',1.59,88,98,5,28,29,'EVISA'],
 ['MU','Маврикий','Бель-Мар',1.48,86,96,4.8,26,28,'VISA_FREE'],['TZ','Танзания','Нунгви',1.14,87,96,4.7,28,30,'EVISA'],
 ['MY','Малайзия','Лангкави',1.12,76,86,4.1,29,31,'VISA_FREE'],['PH','Филиппины','Боракай',1.25,77,97,4.8,28,30,'VISA_FREE'],
 ['IN','Индия','Южный Гоа',.89,80,82,3.8,28,31,'EVISA'],['QA','Катар','Доха',1.12,92,85,4,27,31,'UNKNOWN'],
 ['ES','Испания','Майорка',.77,81,93,4.6,25,27,'VISA_REQUIRED']
] as const;
export const countryOptions=destinations.map(([code,name])=>({code,name}));
export function selectedCountryCodes(f:Filters):string[]{
 if(f.destinationMode!=='Выбранные страны')return [];
 const tokens=String(f.destinations||'').split(/[,;\n]/).map(s=>s.trim().toLocaleLowerCase('ru-RU')).filter(Boolean);
 return countryOptions.filter(({code,name})=>tokens.includes(code.toLowerCase())||tokens.includes(name.toLocaleLowerCase('ru-RU'))||(code==='TH'&&tokens.includes('тайланд'))).map(({code})=>code);
}
export function countryMatches(f:Filters,country:string|undefined|null):boolean{
 if(f.destinationMode!=='Выбранные страны')return true;
 if(!country)return false;
 const selected=selectedCountryCodes(f);
 const value=country.trim().toLocaleLowerCase('ru-RU');
 return selected.some(code=>code.toLowerCase()===value||countryOptions.some(option=>option.code===code&&option.name.toLocaleLowerCase('ru-RU')===value));
}
const kinds=['russian','diy','gatewayPackage','charter','wholesale','foreign'];
const hubs=[['TR','IST','Стамбул'],['AE','DXB','Дубай'],['QA','DOH','Доха'],['OM','MCT','Маскат'],['CN','PEK','Пекин'],['DE','FRA','Франкфурт']];
export const kindLabels:Record<string,string>={russian:'Российский пакет',diy:'Своя сборка',gatewayPackage:'Через gateway',charter:'Чартер + отель',wholesale:'B2B-отель + перелёт',foreign:'Зарубежный пакет'};
export const money=(v:number)=>new Intl.NumberFormat('ru-RU',{style:'currency',currency:'RUB',maximumFractionDigits:0}).format(v);
export const addDays=(d:string,n:number)=>new Date(Date.parse(d+'T12:00:00Z')+n*86400000).toISOString().slice(0,10);
export const shortDate=(d:string)=>new Date(d+'T12:00:00Z').toLocaleDateString('ru-RU',{day:'numeric',month:'short'});
export function validate(f:Filters,p:Party):string[]{
 const errors:string[]=[];
 for(const section of sections)for(const field of section.fields)if(field.type==='number'&&(!Number.isFinite(Number(f[field.key]))||Number(f[field.key])<field.min!||Number(f[field.key])>field.max!))errors.push(`Проверьте поле «${field.label}»`);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(String(f.earliest))||!/^\d{4}-\d{2}-\d{2}$/.test(String(f.latest))||!/^\d{4}-\d{2}-\d{2}$/.test(String(f.latestDeparture)))errors.push('Укажите даты поездки');
 if(f.earliest>f.latest||f.earliest>f.latestDeparture||f.latestDeparture>f.latest)errors.push('Проверьте порядок дат');
 if(f.destinationMode==='Выбранные страны'&&selectedCountryCodes(f).length===0)errors.push('Выберите хотя бы одну страну в блоке «Куда»');
 if(Number(f.minNights)>Number(f.maxNights))errors.push('Минимум ночей не может превышать максимум');
 if(Number(f.dayMin)>Number(f.dayMax))errors.push('Минимальная температура выше максимальной');
 if((Date.parse(String(f.latest))-Date.parse(String(f.earliest)))/86400000>180)errors.push('Окно локального поиска ограничено 180 днями');
 if(!Number.isInteger(p.adults)||p.adults<1||p.adults>8||p.children.length>8||p.children.some(a=>a<0||a>17||!Number.isInteger(a)))errors.push('Укажите 1–8 взрослых и возраст каждого ребёнка 0–17 лет');
 if(Number(f.wWeather)+Number(f.wBeach)+Number(f.wPrice)+Number(f.wConvenience)+Number(f.wHotel)===0)errors.push('Задайте хотя бы один ненулевой вес');
 if(p.split){const children=p.groups.flatMap(g=>g.children);if(p.groups.reduce((a,g)=>a+g.adults,0)!==p.adults||children.length!==p.children.length||new Set(children).size!==p.children.length||children.some(i=>i<0||i>=p.children.length)||p.groups.some(g=>!Number.isInteger(g.adults)||!Number.isInteger(g.minNights)||!Number.isInteger(g.maxNights)||g.adults<1||g.minNights>g.maxNights||g.minNights<1||g.maxNights>60))errors.push('Распределите каждого ребёнка и всех взрослых по группам ровно один раз; каждой группе нужен взрослый и корректный срок');}
 return errors;
}
export function searchMock(f:Filters,p:Party,sources:SearchSourceSettings=defaultSearchSourceSettings):{offers:Offer[];scenarios:number;excluded:number;errors:string[]}{
 const errors=validate(f,p);if(errors.length)return {offers:[],scenarios:0,excluded:0,errors};
 const result:Offer[]=[];let scenarios=0,excluded=0;
 const people=p.adults+p.children.length;const groupDefs=p.split?p.groups:[{name:'Вся семья',adults:p.adults,children:p.children.map((_,i)=>i),minNights:Number(f.minNights),maxNights:Number(f.maxNights)}];
 const combinations:number[][]=[];const combine=(i:number,ns:number[])=>{if(i===groupDefs.length){combinations.push(ns);return;}for(let n=groupDefs[i].minNights;n<=groupDefs[i].maxNights;n++)combine(i+1,[...ns,n]);};combine(0,[]);
 if(combinations.length>3600)return {offers:[],scenarios:0,excluded:0,errors:['Сузьте диапазоны длительности групп']};
 if(f.citizenship!=='RU'||f.passport!=='ordinary')return {offers:[],scenarios:0,excluded:0,errors:[]};
 const airport=String(f.airports).split(',').map(s=>s.trim().toUpperCase()).find(a=>['SVO','DME','VKO',...(Number(f.radius)>=50?['ZIA']:[])].includes(a));
 if(!['москва','moscow'].includes(String(f.origin).trim().toLowerCase())||!airport)return {offers:[],scenarios:0,excluded:0,errors:[]};
 for(let di=0;di<destinations.length;di++){
  const [code,country,resort,factor,weather,beach,water,sea,air,visa]=destinations[di];
  if(!countryMatches(f,code))continue;
  if(visa==='VISA_REQUIRED'&&!f.schengen){excluded++;continue;}
  if((visa==='EVISA'&&!f.evisa)||(visa==='VISA_ON_ARRIVAL'&&!f.voa))continue;
  if(visa==='VISA_REQUIRED'&&!f.newVisa&&!f.schengen&&!String(f.otherVisas).split(',').includes(code))continue;
  const visaCost=['EVISA','VISA_ON_ARRIVAL'].includes(visa)?people*1500:0;
  if(visaCost>Number(f.visaCost)||(visa==='EVISA'&&Number(f.visaDays)<3))continue;
  if(f.uk||f.usa||f.canada){/* Held visas cannot prove destination entry. No fixture requires these visas. */}
  const stars=di%3===0?5:4,rating=8.3+(di%4)*.3,meal=['EG','TR'].includes(code)?'AI':di%3===0?'HB':'BB';
  const sand=di===8?'Коралл':di%5===0?'Мелкий песок':'Песок';
  const entry=di===8?'Глубокий':'Пологий',pontoon=di===8,reef=['EG','MV','ID'].includes(code);
  const retreat=di===11?180:di%3*30+20;const rainy=di%5+3,rain=rainy*14;
  if(stars<Number(f.stars)||rating<Number(f.rating)||Number(f.rooms)<Math.ceil(people/4)||Number(f.rooms)>4||f.familyRoom&&di%2!==0||f.connecting&&di%3!==0||!f.apartments&&di===12||f.privateBeach&&di%3===1||f.kidsPool&&di%4===3||f.kidsClub&&di%3===2||f.waterpark&&di!==0&&di!==1)continue;
  if(f.meal!=='Любое'&&f.meal!==meal||f.sand!=='Любое'&&f.sand!==sand&&!(f.sand==='Песок'&&sand==='Мелкий песок')||f.entry!=='Любой'&&f.entry!==entry||f.noPontoon&&pontoon||f.reef==='Нужен'&&!reef||f.reef==='Без рифа'&&reef)continue;
  if(water<Number(f.water)||water<Number(f.clarity)||water<Number(f.colour)||f.turquoise&&water<4.3||f.maldives&&water<4.8||retreat>Number(f.retreat)||f.lowTideSwim&&retreat>80||f.tides==='HIGH'&&retreat>40||f.tides==='MEDIUM'&&retreat>100||f.tides==='LOW'&&retreat>200)continue;
  if(weather<Number(f.weather)||sea<Number(f.sea)||air<Number(f.dayMin)||air>Number(f.dayMax)||rain>Number(f.rain)||rainy>Number(f.rainyDays)||f.monsoon&&di===12||f.typhoon&&di===13)continue;
  for(let ki=0;ki<kinds.length;ki++){
   const kind=kinds[ki];
   const enabled=kind==='russian'?sources.search_tour_operators&&sources.search_russian_operators:kind==='foreign'||kind==='gatewayPackage'?sources.search_tour_operators&&sources.search_foreign_operators&&sources.allow_foreign_package_positioning:kind==='wholesale'||kind==='charter'?sources.search_wholesalers:sources.search_retail_diy;
   if(!enabled)continue;
   const hasGateway=kind==='gatewayPackage'||kind==='foreign';
   if(hasGateway&&!f.gateway)continue;
   const possibleHubs=hasGateway?hubs:[['','','']];
   for(const [hubCode,hub,hubName]of possibleHubs){
    if(!f.schengen&&hubCode==='DE'){excluded++;continue;}
    if(hasGateway&&f.gatewayCountries!=='AUTO'&&f.gatewayCountries!==hubCode)continue;
    const stops=hasGateway?1:di%4===2?1:0,flightHours=5+di*.45+(hasGateway?5:0),position=hasGateway?52000+people*1800:0;
    const recommended=Math.max(sources.positioning_min_buffer_hours,12+(p.children.length?6:0)+6+4);const actualBuffer=hasGateway?30:0;
    const positionDuration=hasGateway?5:0;
    if(f.direct&&stops>0||stops>Number(f.stops)||Number(f.baggage)>23||Number(f.carryOn)>8||flightHours>Number(f.flightHours)||hasGateway&&(!sources.positioning_self_transfer_allowed||!sources.positioning_overnight_allowed||actualBuffer>Number(f.layover)||actualBuffer<recommended||(sources.positioning_max_price!==null&&position>sources.positioning_max_price)||(sources.positioning_max_duration_hours!==null&&positionDuration>sources.positioning_max_duration_hours)))continue;
    let best:Offer|undefined;
    const firstDeparture=String(f.earliest)>new Date().toLocaleDateString('sv-SE')?String(f.earliest):new Date().toLocaleDateString('sv-SE');
    for(let departure=firstDeparture;departure<=String(f.latestDeparture);departure=addDays(departure,1))for(const ns of combinations){
     scenarios++;const returns=ns.map(n=>addDays(departure,n));if(returns.some(r=>r>String(f.latest)))continue;
     if(f.passportExpiry&&String(f.passportExpiry)<addDays([...returns].sort().at(-1)!,180))continue;
     const weekday=new Date(departure).getUTCDay();const dateFactor=weekday===2||weekday===3?.95:1.04;
     const bedNights=ns.reduce((sum,n,i)=>sum+n*(groupDefs[i].adults+groupDefs[i].children.reduce((s,j)=>s+(p.children[j]<2?.1:p.children[j]<12?.6:.9),0)),0);
     const airPeople=p.adults+p.children.reduce((sum,a)=>sum+(a<2?.1:a<12?.8:1),0);
     const base=Math.round((14500*airPeople+4300*bedNights+1800*Number(f.rooms)*Math.max(...ns))*factor*dateFactor);
     const costs:{label:string;amount:number;currency:string;original:number;included?:boolean}[]=[];
     const push=(label:string,amount:number)=>costs.push({label,amount:Math.round(amount),currency:'RUB',original:Math.round(amount)});
     const pack=['russian','foreign','gatewayPackage'].includes(kind);
     push(pack?'Пакет: перелёт и проживание':'Перелёты туда и обратно',pack?base*(hasGateway?.68:1):base*.43);
     if(!pack)push('Проживание всех групп',base*(kind==='wholesale'?.44:.50));
      const gatewayHotel=hasGateway?16000+(p.split?8000:0):0;
      if(hasGateway){push('Перелёты до gateway и обратно',position);push('Ночёвки в gateway в обе стороны',gatewayHotel);push('Питание во время пересадок',people*1600);}
     push('Багаж и обязательные сборы',people*2200);push('Трансферы',9000+(p.split?4500:0));push('Визы и разрешения',visaCost);push('Налоги отеля и курортные сборы',Math.max(...ns)*people*100);push('Обязательная страховка',people*900);push('Комиссии оплаты и конвертации',base*.015);
     if(di===10||di===11)push('Паром / автобус',people*2400);
      const price=costs.reduce((s,c)=>s+c.amount,0);if(price>Number(f.budget)||Number(f.perPerson)>0&&price/people>Number(f.perPerson))continue;
      const packagePrice=costs[0]?.amount||0,additionalCosts=price-packagePrice;
     const convenience=Math.max(0,100-flightHours*2-(hasGateway?18:0)+(f.directPreferred&&stops===0?8:0));
     const weights=[Number(f.wWeather)*Number(f.weatherImportance)/3,Number(f.wBeach),Number(f.wPrice),Number(f.wConvenience),Number(f.wHotel)];
     const value=Math.max(0,100-price/Number(f.budget)*50);const metrics=[weather,beach,value,convenience,rating*10];
     const preference=f.countryMeals&&((['TR','EG'].includes(code)&&meal==='AI')||(['TH','VN','LK','MY','PH','ID'].includes(code)&&meal==='BB'))?2:0;
     const score=Math.min(100,Math.round(metrics.reduce((s,v,i)=>s+v*weights[i],0)/weights.reduce((a,b)=>a+b,0)+preference));
     const route=[airport,...(hasGateway?[hub]:[]),resort,...(di===10||di===11?['Автобус','Паром']:[])];
      const operatorName=kind==='russian'?'Российский туроператор (демо)':hasGateway?`${hubName} Holidays (демо)`:kind==='wholesale'?'B2B wholesale (демо)':kind==='charter'?'Charter provider (демо)':'Retail suppliers (демо)';
      const operatorCountry=kind==='russian'?'Россия':hasGateway?hubName:'';
      const offer:Offer={searchParty:JSON.parse(JSON.stringify(p)),searchRooms:Number(f.rooms),id:`${code}-${kind}-${hub||'direct'}-${departure}-${ns.join('-')}`,country,code,resort,hotel:`${resort} · семейный отель ${stars}★`,kind,meal,departure,returns,nights:ns,people,price,costs,weather,beach,water,family:di%3===0?96:87,score,sea,air,stars,rating,gateway:hasGateway?`${hubName} · ${hub}`:'',gatewayCountry:hubCode,route,risk:hasGateway?48:stops?24:12,bookingRisk:hasGateway?76:60,buffer:actualBuffer,visa,source:'Демонстрационный поставщик',sourceUrl:'',savings:null,comparisonKey:`${code}-${departure}-${ns.join('-')}-${meal}-${f.rooms}-${JSON.stringify(groupDefs)}`,explanation:hasGateway?'Полная модель: зарубежный пакет, positioning flights, gateway hotel, багаж, трансферы, визовые и обязательные расходы.':'Модель полной стоимости для всей семьи. Это пример расчёта, не предложение продавца.',demo:true,available:false,access_status:'MOCK',pricing_reality:'SYNTHETIC',bookable:false,flightHours,groupLabels:groupDefs.map(g=>`${g.name}: ${g.adults} взр. + ${g.children.length} дет.`),reasons:['Все цены, отели, погодные и пляжные оценки — синтетические','Виза и доступность не проверены; бронирование отсутствует'],operatorName,operatorCountry,startAirport:hasGateway?hub:'',positioningCost:position,gatewayHotelCost:gatewayHotel,overnightNeeded:hasGateway,selfTransfer:hasGateway,visaDecision:visa==='VISA_REQUIRED'?'REQUIRED':'CHECK',packagePrice,additionalCosts,totalRealCost:price};
     if(!best||offer.price<best.price)best=offer;
    }
    if(best)result.push(best);
   }
  }
 }
 for(const o of result){const baseline=result.find(b=>b.kind==='russian'&&b.comparisonKey===o.comparisonKey);if(baseline&&o.kind!=='russian')o.savings=baseline.price-o.price;}
 return {offers:result.sort((a,b)=>b.score-a.score||a.price-b.price),scenarios,excluded,errors};
}
