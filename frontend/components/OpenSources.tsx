'use client';

import {ExternalLink} from 'lucide-react';
import {selectedCountryCodes,type Filters,type Party} from '@/lib/search';

const sources = [
  {name:'Travelata',type:'Агрегатор пакетных туров',url:'https://travelata.ru/',countries:{EG:'https://travelata.ru/egypt/october',TH:'https://travelata.ru/thailand/october',TR:'https://travelata.ru/turkey/october',MV:'https://travelata.ru/maldives/october'}},
  {name:'Onlinetours',type:'Агрегатор пакетных туров',url:'https://www.onlinetours.ru/',countries:{EG:'https://www.onlinetours.ru/tury/egypt/v_oktyabre',TH:'https://www.onlinetours.ru/tury/thailand'}},
  {name:'1001 Тур',type:'Агентство, предложения разных операторов',url:'https://www.1001tur.ru/',countries:{EG:'https://www.1001tur.ru/egypt/tury/month_october/',TH:'https://www.1001tur.ru/tailand/tury/month_october/',TR:'https://www.1001tur.ru/turkey/tury/alanya/month_october/',VN:'https://www.1001tur.ru/vietnam/tury/month_october/',MV:'https://www.1001tur.ru/maldives/tury/month_october/'}},
  {name:'Coral Travel',type:'Туроператор',url:'https://www.coral.ru/main/',countries:{EG:'https://www.coral.ru/main/egypt/'}},
  {name:'PEGAS Touristik',type:'Туроператор, публичный агентский каталог',url:'https://agency.pegast.ru/agent',countries:{}},
  {name:'ANEX Tour',type:'Туроператор, публичный конструктор',url:'https://b2ctr.anextour.com/',countries:{}},
  {name:'Библио-Глобус',type:'Туроператор',url:'https://www.bgoperator.ru/',countries:{}},
] as const;

export default function OpenSources({filters,party}:{filters:Filters;party:Party}) {
  const selected=selectedCountryCodes(filters);
  const target=selected.length===1?selected[0]:null;
  const octoberInWindow=String(filters.earliest)<='2026-10-31'&&String(filters.latestDeparture)>='2026-10-01';
  return <section className="open-source-directory" aria-labelledby="open-source-directory-title">
    <h3 id="open-source-directory-title">Открытые сайты туроператоров и агентств</h3>
    <p>Это дополнительные места для проверки туров. Ссылки ведут на публичный каталог или форму продавца; цена по вашим параметрам не получена и в расчёт не включена.</p>
    <p className="hint">Ваш запрос: {target||'любой пляж'} · вылет {filters.earliest}–{filters.latestDeparture} · {filters.minNights}–{filters.maxNights} ночей · {party.adults} взрослых и {party.children.length} детей ({party.children.join(', ')||'нет'} лет). Проверьте эти данные, питание и багаж на сайте продавца.</p>
    <div className="source-grid">{sources.map(source=>{
      const focused=target?source.countries as Record<string,string>:{};
      const focusedOctober=!!target&&octoberInWindow&&!!focused[target];
      const url=focusedOctober?focused[target!]:source.url;
      return <article key={source.name}>
        <h4>{source.name}</h4><p>{source.type}</p>
        <p className="hint">DEEPLINK · цена не получена · параметры нужно подтвердить на сайте</p>
        <a href={url} target="_blank" rel="noopener noreferrer">Открыть {focusedOctober?'каталог направления за октябрь':'поиск'} <ExternalLink size={14}/></a>
      </article>;
    })}</div>
  </section>;
}
