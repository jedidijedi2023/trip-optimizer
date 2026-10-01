'use client';
import {useState} from 'react';
import {Database,ExternalLink,CheckCircle2,Circle,LoaderCircle} from 'lucide-react';
import {countryMatches,type Filters} from '@/lib/search';

type Money={original_amount:string;original_currency:string};
type Provenance={provider:string;access_status:string;pricing_reality:string;bookable:boolean|null;source_url:string};
type LiveOffer={id:string;kind:string;provenance:Provenance;price:Money;hotel?:{name:string;country:string}|null;room?:string|null;meal?:string|null;booking_url?:string|null;raw_reference?:string|null;cancellation?:unknown;payment_terms?:string|null;mandatory_costs_complete?:boolean};
type Attempted={provider:string;connected:boolean;used:boolean;count:number;note:string|null};
type ProviderRow={provider:string;access_status:string;connected:boolean;env_hint:string;integration_note:string;source_url:string};

export default function LiveOffers({offers,attempted,providers,message,busy,onSearch,filters,apiAvailable=true}:{
 offers:LiveOffer[];attempted:Attempted[];providers:ProviderRow[];message:string|null;busy:boolean;onSearch:()=>void;filters:Filters;apiAvailable?:boolean;
}){
 const [detail,setDetail]=useState<LiveOffer|null>(null);
 const relevant=providers.filter(p=>attempted.some(a=>a.provider===p.provider)||p.connected);
 const visibleOffers=offers.filter(o=>countryMatches(filters,o.hotel?.country));
 return <>
  <div className="empty live-empty" style={{textAlign:'left'}}>
   <div style={{display:'flex',alignItems:'center',gap:12}}><Database size={32}/><div><h3 style={{margin:0}}>{busy?'Проверяем подключённые источники…':visibleOffers.length?`Найдено предложений: ${visibleOffers.length}`:'Подключённых предложений для выбранных стран пока нет'}</h3><p style={{margin:0}}>{message||'Запустите поиск, чтобы проверить подключённые источники.'}</p>{!busy&&offers.length>visibleOffers.length&&<p className="hint">{offers.length-visibleOffers.length} тестовых предложений скрыто: страна не совпадает с выбранной или не указана.</p>}</div></div>
   <button onClick={onSearch} disabled={busy||!apiAvailable}>{busy?<><LoaderCircle className="spin" size={16}/> Поиск…</>:apiAvailable?'Проверить источники':'Для проверки нужен API'}</button>
  </div>

  {attempted.length>0&&<div className="source-check-results" role="status"><strong>Проверка завершена</strong>{attempted.map(a=><p key={a.provider}>{a.provider}: {a.used?`запрос выполнен, получено ${a.count}`:a.connected?'запрос не выполнен':'нет доступа'}{a.note?` · ${a.note}`:''}</p>)}</div>}
  {visibleOffers.length>0&&<div className="cards">{visibleOffers.map(o=><article className="offer" key={o.id}>
   <div className="offer-main">
    <div className="offer-heading"><span className="demo-tag">{o.provenance.access_status}</span><span className="demo-tag">{o.provenance.pricing_reality}</span></div>
    <h3>{o.hotel?.name||o.kind}</h3>
    {o.room&&<p className="offer-date">{o.room}</p>}
    {o.meal&&<div className="chips"><span>{o.meal}</span></div>}
    <p className="hint">Источник: {o.provenance.provider} · Бронирование: {o.provenance.bookable===true?'подтверждено':'не подтверждено'}</p>
   </div>
   <div className="offer-price"><div className="price-block"><small>{o.provenance.access_status} · {o.provenance.pricing_reality}</small><strong>{o.price.original_amount} {o.price.original_currency}</strong></div>
   <button className="details-button" onClick={()=>setDetail(o)}>Подробнее и покупка</button>
   {o.provenance.source_url.startsWith('https://')&&<a href={o.provenance.source_url} target="_blank" rel="noreferrer">Документация <ExternalLink size={14}/></a>}</div>
  </article>)}</div>}

  {detail&&visibleOffers.some(o=>o.id===detail.id)&&<section className="purchase-details" role="region" aria-label="Детали предложения"><button className="text-button" onClick={()=>setDetail(null)}>Закрыть детали</button><h3>{detail.hotel?.name||detail.kind}</h3><p>Источник: {detail.provenance.provider} · {detail.provenance.access_status} · {detail.provenance.pricing_reality}</p><strong>{detail.price.original_amount} {detail.price.original_currency}</strong><p>Номер: {detail.room||'не указан'} · Питание: {detail.meal||'не указано'}</p><p>Идентификатор предложения: {detail.raw_reference||detail.id}</p><p>Все обязательные расходы: {detail.mandatory_costs_complete?'учтены':'не подтверждены'}. Условия оплаты: {detail.payment_terms||'не подтверждены'}.</p>{detail.cancellation!=null&&<details><summary>Условия отмены от поставщика</summary><pre>{JSON.stringify(detail.cancellation,null,2)}</pre></details>}{detail.provenance.access_status==='LIVE'&&detail.provenance.pricing_reality==='REAL'&&detail.provenance.bookable===true&&detail.booking_url?.startsWith('https://')?<a className="primary" href={detail.booking_url} target="_blank" rel="noopener noreferrer">Перейти к покупке у продавца <ExternalLink size={16}/></a>:<div className="notice"><p>Ссылка на покупку этого тарифа отсутствует. Demo/sandbox нельзя приобрести по показанной цене. Документация поставщика не является страницей бронирования.</p></div>}</section>}
  <section className="search-sources" aria-labelledby="live-connection-title">
   <div className="source-settings-head"><div><span className="eyebrow">СТАТУС ИСТОЧНИКОВ</span><h2 id="live-connection-title">Что подключено прямо сейчас</h2></div></div>
   <div className="source-grid">{relevant.map(p=><article key={p.provider}>
    <div style={{display:'flex',alignItems:'center',gap:8}}>{p.connected?<CheckCircle2 size={18}/>:<Circle size={18}/>}<h3 style={{margin:0}}>{p.provider}</h3></div>
    <p>{p.connected?'Подключено':'Требуется регистрация'}{!p.connected&&p.env_hint!=='—'&&<> · переменные: <code>{p.env_hint}</code></>}</p>
    <p className="hint">{p.integration_note}</p>
    {p.source_url.startsWith('https://')&&<a href={p.source_url} target="_blank" rel="noreferrer">Документация поставщика <ExternalLink size={14}/></a>}
   </article>)}</div>
  </section>
 </>;
}
