'use client';
import {useEffect,useMemo,useState} from 'react';
import {ExternalLink,Info} from 'lucide-react';
import {countryMatches,defaults,defaultParty,type Filters,type Party} from '@/lib/search';
import bundled from '@/data/public_price_observations.json';
import {apiAvailable,apiBaseUrl} from '@/lib/api';

type Expense={label:string;amount?:number;source_url?:string;note?:string};
type Observation={id:string;provider:string;title:string;amount:number;currency:string;travellers:string;dates:string;source_url:string;limitations:string[];access_status:'DEEPLINK';pricing_reality:'LIMITED_REAL';bookable:boolean|null;observed_at?:string;kind?:'FLIGHT'|'PACKAGE';country_code?:string;origin?:string;destination?:string;departure?:string;return_date?:string;adults?:number;children_ages?:number[]|null;baggage_kg?:number;airport_change?:boolean;purchase_url?:string;expenses?:Expense[];alternatives?:{label:string;amount:number;source_url:string}[]};
type Catalogue={observed_at:string;automatic_refresh:boolean;observations:Observation[]};
const api=apiBaseUrl;
function rub(amount:number,currency:string){try{return new Intl.NumberFormat('ru-RU',{style:'currency',currency,maximumFractionDigits:0}).format(amount)}catch{return `${amount.toLocaleString('ru-RU')} ${currency}`}}
function fresh(o:Observation,c:Catalogue,now:number|null){const t=Date.parse(o.observed_at||c.observed_at);return now!==null&&Number.isFinite(t)&&now-t<12*3600000&&now>=t-3600000;}
function exactMatch(o:Observation,f:Filters,p:Party){
 if(!o.departure||!o.return_date||o.departure<String(f.earliest)||o.departure>String(f.latestDeparture)||o.return_date>String(f.latest))return false;
 if(o.adults!==p.adults||!o.children_ages||JSON.stringify([...o.children_ages].sort((a,b)=>a-b))!==JSON.stringify([...p.children].sort((a,b)=>a-b)))return false;
 if(o.origin&&!String(f.airports).split(',').map(s=>s.trim().toUpperCase()).includes(o.origin))return false;
 if(o.baggage_kg!==undefined&&o.baggage_kg<Number(f.baggage)||o.airport_change&&!f.airportChange)return false;
 if(!countryMatches(f,o.country_code))return false;
 return true;
}
function expenseLines(o:Observation,current:boolean):Expense[]{
 if(o.expenses?.length)return o.expenses;
 return o.kind==='PACKAGE'?[{label:'Опубликованная цена пакетного тура',amount:o.amount,source_url:o.source_url},{label:'Обязательные доплаты и сборы'},{label:'Трансфер и расходы вне пакета'},{label:'Страховка и визы'}]:[{label:'Перелёт туда и обратно',amount:o.amount,source_url:current?o.purchase_url||o.source_url:o.source_url},{label:'Багаж до требований поиска'},{label:'Проживание на весь срок'},{label:'Трансферы и наземный транспорт'},{label:'Визы, страховка, обязательные сборы'}];
}
export default function PublicPrices({filters=defaults,party=defaultParty}:{filters?:Filters;party?:Party}){
 const [catalogue,setCatalogue]=useState<Catalogue>(bundled as Catalogue),[selected,setSelected]=useState<string|null>(null),[server,setServer]=useState(false),[clock,setClock]=useState<number|null>(null);
 useEffect(()=>{setClock(Date.now())},[]);
 useEffect(()=>{if(!apiAvailable)return;let active=true;fetch(api+'/api/public-prices',{signal:AbortSignal.timeout(8000)}).then(r=>r.ok?r.json():null).then(v=>{if(active&&v?.observations){setCatalogue(v);setServer(true)}}).catch(()=>{if(active)setServer(false)});return()=>{active=false}},[]);
 const list=useMemo(()=>catalogue.observations.filter(o=>countryMatches(filters,o.country_code)).sort((a,b)=>Number(exactMatch(b,filters,party))-Number(exactMatch(a,filters,party))||Date.parse(b.observed_at||catalogue.observed_at)-Date.parse(a.observed_at||catalogue.observed_at)),[catalogue,filters,party]);
 const chosen=list.find(o=>o.id===selected);
 return <section className="public-prices" aria-labelledby="public-price-title"><h3 id="public-price-title">Цены с открытых страниц продавцов</h3>
 <p>{list.length} опубликованных наблюдений · {server?'каталог сервера':'сохранённый каталог'} · автоматическое обновление: {catalogue.automatic_refresh?'да':'нет'}. Цена и наличие могут измениться при переходе; сравнивайте только одинаковые даты, пассажиров, багаж и условия.</p>
 {list.length===0&&<p className="hint" role="status">Для выбранных стран в каталоге открытых цен пока нет. Предложения других стран скрыты.</p>}
 <div className="public-price-grid">{list.map(o=>{const matching=exactMatch(o,filters,party),isFresh=fresh(o,catalogue,clock);return <article key={o.id}><span className="observation-tag">{o.access_status} · {o.pricing_reality} · {isFresh?'СНИМОК МЛАДШЕ 12 Ч':'АРХИВНЫЙ СНИМОК'} · {matching?'ПАРАМЕТРЫ СОВПАДАЮТ':'НЕ ВСЕ ПАРАМЕТРЫ СОВПАДАЮТ'}</span><h4>{o.title}</h4><strong>{rub(o.amount,o.currency)}</strong><p>{o.provider} · {o.dates}</p><p>{o.travellers}</p><p className="hint">Снято: {new Date(o.observed_at||catalogue.observed_at).toLocaleString('ru-RU',{timeZone:'Europe/Moscow'})}. {o.kind==='PACKAGE'?'Опубликованная цена пакета':'Перелёт'}; полная стоимость поездки не определена.</p><button type="button" className="details-button" onClick={()=>setSelected(old=>old===o.id?null:o.id)}>Подробнее и все расходы</button><a href={isFresh&&o.purchase_url?o.purchase_url:o.source_url} target="_blank" rel="noopener noreferrer">{isFresh&&o.purchase_url?'Открыть выбранный вариант':'Открыть источник цены'} <ExternalLink size={14}/></a></article>})}</div>
 {chosen&&<div className="public-price-detail" role="region" aria-label={'Расходы: '+chosen.title}><button type="button" onClick={()=>setSelected(null)}>Закрыть</button><h3>{chosen.title}</h3><p>{chosen.provider} · {chosen.dates} · {chosen.travellers}</p><div className="cost-table">{expenseLines(chosen,fresh(chosen,catalogue,clock)).map((e,i)=><div key={i}><span>{e.label}{e.note&&<small>{e.note}</small>}{e.source_url&&<small className="price-source"><a href={e.source_url} target="_blank" rel="noopener noreferrer">Предложение и источник цены ↗</a></small>}</span><strong>{e.amount!==undefined?rub(e.amount,chosen.currency):'Не найдена'}</strong></div>)}</div>{!!chosen.alternatives?.length&&<><h4>Другие тарифы этой выдачи · не складывать</h4><div className="cost-table">{chosen.alternatives.map((a,i)=><div key={i}><span>{a.label}<small className="price-source"><a href={a.source_url} target="_blank" rel="noopener noreferrer">Проверить на сайте ↗</a></small></span><strong>{rub(a.amount,chosen.currency)}</strong></div>)}</div></>}<h4>Полная стоимость поездки: не определена</h4><p>Найденная сумма относится только к указанному компоненту. Другие строки требуют проверяемых цен и ссылок; неподтверждённые расходы не считаются нулём.</p><ul>{chosen.limitations.map((l,i)=><li key={i}>{l}</li>)}</ul><a href={chosen.source_url} target="_blank" rel="noopener noreferrer">Открыть исходную выдачу <ExternalLink size={14}/></a>{chosen.purchase_url&&fresh(chosen,catalogue,clock)&&<> · <a href={chosen.purchase_url} target="_blank" rel="noopener noreferrer">Открыть страницу выбранного тарифа <ExternalLink size={14}/></a></>}</div>}
 <div className="notice"><Info size={18}/><p>Источник подтверждает только факт публикации цены при наблюдении. Синтетические и sandbox цены сюда не включаются. Архивные и несовпадающие варианты не участвуют в расчёте экономии.</p></div></section>;
}
