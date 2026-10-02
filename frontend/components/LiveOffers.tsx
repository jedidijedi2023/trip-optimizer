'use client';
import {useEffect,useRef,useState} from 'react';
import {Database,ExternalLink,CheckCircle2,Circle,LoaderCircle} from 'lucide-react';
import {countryMatches,type Filters} from '@/lib/search';

type Money={original_amount:string;original_currency:string};
type Provenance={provider:string;access_status:string;pricing_reality:string;bookable:boolean|null;source_url:string};
type LiveOffer={id:string;kind:string;provenance:Provenance;price:Money;hotel?:{name:string;country:string}|null;room?:string|null;meal?:string|null;booking_url?:string|null;search_url?:string|null;origin?:string|null;destination?:string|null;country_code?:string|null;departure_date?:string|null;return_date?:string|null;passenger_price_scope?:string|null;raw_reference?:string|null;cancellation?:unknown;payment_terms?:string|null;mandatory_costs_complete?:boolean};
type Attempted={provider:string;connected:boolean;used:boolean;count:number;note:string|null};
type ProviderRow={provider:string;access_status:string;connected:boolean;env_hint:string;integration_note:string;source_url:string};

export default function LiveOffers({offers,attempted,providers,message,busy,onSearch,filters,apiAvailable=true}:{
 offers:LiveOffer[];attempted:Attempted[];providers:ProviderRow[];message:string|null;busy:boolean;onSearch:()=>void;filters:Filters;apiAvailable?:boolean;
}){
 const [detail,setDetail]=useState<LiveOffer|null>(null);
 const detailRef=useRef<HTMLDialogElement>(null);
 const relevant=providers.filter(p=>attempted.some(a=>a.provider===p.provider)||p.connected);
 const visibleOffers=offers.filter(o=>countryMatches(filters,o.country_code||o.hotel?.country));
 const visibleDetail=detail&&visibleOffers.some(o=>o.id===detail.id)?detail:null;
 useEffect(()=>{const d=detailRef.current;if(visibleDetail&&!d?.open)d?.showModal();if(!visibleDetail&&d?.open)d.close();return()=>{if(d?.open)d.close()}},[visibleDetail]);
 return <>
  <div className="empty live-empty" style={{textAlign:'left'}}>
   <div style={{display:'flex',alignItems:'center',gap:12}}><Database size={32}/><div><h3 style={{margin:0}}>{busy?'Проверяем подключённые источники…':visibleOffers.length?`Найдено предложений: ${visibleOffers.length}`:'Подключённых предложений для выбранных стран пока нет'}</h3><p style={{margin:0}}>{message||'Запустите поиск, чтобы проверить подключённые источники.'}</p>{!busy&&offers.length>visibleOffers.length&&<p className="hint">{offers.length-visibleOffers.length} тестовых предложений скрыто: страна не совпадает с выбранной или не указана.</p>}</div></div>
   <button onClick={onSearch} disabled={busy||!apiAvailable}>{busy?<><LoaderCircle className="spin" size={16}/> Поиск…</>:apiAvailable?'Проверить источники':'Для проверки нужен API'}</button>
  </div>

  {attempted.length>0&&<div className="source-check-results" role="status"><strong>Проверка завершена</strong>{attempted.map(a=><p key={a.provider}>{a.provider}: {a.used?`запрос выполнен, получено ${a.count}`:a.connected?'запрос не выполнен':'нет доступа'}{a.note?` · ${a.note}`:''}</p>)}</div>}
  {visibleOffers.length>0&&<div className="cards">{visibleOffers.map(o=><article className="offer" key={o.id}>
   <div className="offer-main">
    <div className="offer-heading"><span className="demo-tag">{o.provenance.access_status}</span><span className="demo-tag">{o.provenance.pricing_reality}</span></div>
    <h3>{o.hotel?.name||(o.kind==='FLIGHT'?`${o.origin||'?'} → ${o.destination||'?'}`:o.kind)}</h3>
    {o.departure_date&&<p className="offer-date">{o.departure_date}{o.return_date?' — '+o.return_date:''}</p>}
    {o.room&&<p className="offer-date">{o.room}</p>}
    {o.meal&&<div className="chips"><span>{o.meal}</span></div>}
    <p className="hint">Источник: {o.provenance.provider} · Бронирование: {o.provenance.bookable===true?'подтверждено':'не подтверждено'}</p>
   </div>
   <div className="offer-price"><div className="price-block"><small>{o.kind==='FLIGHT'?'Кэшированная цена билета':'Цена компонента'} · {o.provenance.pricing_reality}</small><strong>{o.price.original_amount} {o.price.original_currency}</strong><span>Полная стоимость семьи не рассчитана</span></div>
   <button className="details-button" onClick={()=>setDetail(o)}>Подробнее и расходы</button>
   {o.search_url?.startsWith('https://www.aviasales.ru/search/')&&<a href={o.search_url} target="_blank" rel="noopener noreferrer">Открыть поиск Aviasales <ExternalLink size={14}/></a>}
   {o.provenance.source_url.startsWith('https://')&&<a href={o.provenance.source_url} target="_blank" rel="noreferrer">Документация <ExternalLink size={14}/></a>}</div>
  </article>)}</div>}

  <dialog ref={detailRef} className="dialog" onCancel={()=>setDetail(null)}><header><h2>Детали предложения и расходы</h2><button type="button" aria-label="Закрыть" onClick={()=>setDetail(null)}>✕</button></header>{visibleDetail&&<div className="modal-body"><h3>{visibleDetail.hotel?.name||(visibleDetail.kind==='FLIGHT'?`${visibleDetail.origin} → ${visibleDetail.destination}`:visibleDetail.kind)}</h3><p>{visibleDetail.provenance.provider} · {visibleDetail.provenance.access_status} · {visibleDetail.provenance.pricing_reality}</p><p>{visibleDetail.departure_date}{visibleDetail.return_date?' — '+visibleDetail.return_date:''}</p><p className="hint">{visibleDetail.passenger_price_scope||'Состав семьи, возможность бронирования и полная стоимость не подтверждены.'}</p><div className="cost-table"><div><span>{visibleDetail.kind==='FLIGHT'?'Цена билета из кэша':'Предложение поставщика'}{visibleDetail.search_url&&<small className="price-source"><a href={visibleDetail.search_url} target="_blank" rel="noopener noreferrer">Проверить выдачу у продавца ↗</a></small>}</span><strong>{visibleDetail.price.original_amount} {visibleDetail.price.original_currency}</strong></div>{(visibleDetail.kind==='FLIGHT'?['Билеты для остальных членов семьи','Багаж и сборы','Проживание всех групп','Трансферы','Визы и страховка']:['Перелёт всей семьи','Трансферы','Визы и страховка','Прочие обязательные сборы']).map(label=><div key={label}><span>{label}</span><strong>Не найдена</strong></div>)}</div><h4>Полная стоимость: не определена</h4><p>Неизвестные расходы не считаются нулём. Demo/sandbox и кэшированные цены не доказывают экономию.</p><p>Идентификатор: {visibleDetail.raw_reference||visibleDetail.id}</p>{visibleDetail.cancellation!=null&&<details><summary>Условия отмены</summary><pre>{JSON.stringify(visibleDetail.cancellation,null,2)}</pre></details>}{visibleDetail.provenance.access_status==='LIVE'&&visibleDetail.provenance.pricing_reality==='REAL'&&visibleDetail.provenance.bookable===true&&visibleDetail.booking_url?.startsWith('https://')?<a className="primary" href={visibleDetail.booking_url} target="_blank" rel="noopener noreferrer">К продавцу <ExternalLink size={16}/></a>:<div className="notice"><p>Подтверждённой ссылки на покупку этого тарифа нет. Ссылка поиска открывает новую выдачу и требует повторной проверки цены.</p></div>}</div>}</dialog>
  <section className="search-sources" aria-labelledby="live-connection-title">
   <div className="source-settings-head"><div><span className="eyebrow">СТАТУС ИСТОЧНИКОВ</span><h2 id="live-connection-title">Что подключено прямо сейчас</h2></div></div>
   <div className="source-grid">{relevant.map(p=><article key={p.provider}>
    <div style={{display:'flex',alignItems:'center',gap:8}}>{p.connected?<CheckCircle2 size={18}/>:<Circle size={18}/>}<h3 style={{margin:0}}>{p.provider}</h3></div>
    <p>{p.connected?'Подключено':p.provider==='Travelpayouts / Aviasales Data API'?'Токен не настроен на сервере':'Доступ не настроен на сервере'}{!p.connected&&p.env_hint!=='—'&&<> · переменные: <code>{p.env_hint}</code></>}</p>
    {!p.connected&&p.provider==='Travelpayouts / Aviasales Data API'&&<p className="hint">Добавьте собственный токен в Render → backend-сервис → Environment как <code>TRAVELPAYOUTS_TOKEN</code>. Не размещайте его в публичном GitHub или переменных <code>NEXT_PUBLIC_*</code>.</p>}
    <p className="hint">{p.integration_note}</p>
    {p.source_url.startsWith('https://')&&<a href={p.source_url} target="_blank" rel="noreferrer">Документация поставщика <ExternalLink size={14}/></a>}
   </article>)}</div>
  </section>
 </>;
}
