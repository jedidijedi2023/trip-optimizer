'use client';
import {Plane,PackageSearch,Boxes,ShoppingBag,ShieldCheck} from 'lucide-react';
import type {SearchSourceSettings} from '@/lib/search';

export default function SearchSources({value,onChange}:{value:SearchSourceSettings;onChange:(value:SearchSourceSettings)=>void}){
 const set=<K extends keyof SearchSourceSettings>(key:K,next:SearchSourceSettings[K])=>onChange({...value,[key]:next});
 const number=(raw:string)=>raw===''?null:Number(raw);
 return <section className="search-sources" aria-labelledby="search-sources-title">
  <div className="source-settings-head"><div><span className="eyebrow">ПАРАЛЛЕЛЬНЫЙ ПОИСК</span><h2 id="search-sources-title">ИСТОЧНИКИ ПОИСКА</h2></div><span><ShieldCheck size={16}/> Визовый фильтр применяется до поиска зарубежного пакета</span></div>
  <div className="source-settings-grid">
   <article className={value.search_tour_operators?'enabled':''}><label className="source-master"><PackageSearch size={21}/><span><b>Искать у туроператоров</b><small>Российские и зарубежные пакетные предложения</small></span><input type="checkbox" checked={value.search_tour_operators} onChange={e=>set('search_tour_operators',e.target.checked)}/></label>
    <div className="source-nested" aria-disabled={!value.search_tour_operators}>
     <label><input type="checkbox" disabled={!value.search_tour_operators} checked={value.search_russian_operators} onChange={e=>set('search_russian_operators',e.target.checked)}/> Российские туроператоры</label>
     <label><input type="checkbox" disabled={!value.search_tour_operators} checked={value.search_foreign_operators} onChange={e=>set('search_foreign_operators',e.target.checked)}/> Зарубежные туроператоры</label>
     <label><input type="checkbox" disabled={!value.search_tour_operators||!value.search_foreign_operators} checked={value.allow_foreign_package_positioning} onChange={e=>set('allow_foreign_package_positioning',e.target.checked)}/> Подбирать перелёт до аэропорта старта тура</label>
     {value.search_tour_operators&&value.search_foreign_operators&&value.allow_foreign_package_positioning&&<div className="positioning-settings">
      <div><label>Макс. цена, ₽<input type="number" min="0" placeholder="Без лимита" value={value.positioning_max_price??''} onChange={e=>set('positioning_max_price',number(e.target.value))}/></label><label>Макс. время, ч<input type="number" min="0" max="168" placeholder="Без лимита" value={value.positioning_max_duration_hours??''} onChange={e=>set('positioning_max_duration_hours',number(e.target.value))}/></label><label>Мин. запас, ч<input type="number" min="1" max="168" value={value.positioning_min_buffer_hours} onChange={e=>set('positioning_min_buffer_hours',Math.max(1,Number(e.target.value)||1))}/></label></div>
      <label><input type="checkbox" checked={value.positioning_overnight_allowed} onChange={e=>set('positioning_overnight_allowed',e.target.checked)}/> Разрешить ночёвку</label><label><input type="checkbox" checked={value.positioning_self_transfer_allowed} onChange={e=>set('positioning_self_transfer_allowed',e.target.checked)}/> Разрешить самостоятельную пересадку</label>
      <p><Plane size={14}/> Россия → gateway → пакет → gateway → Россия. При отсутствии Шенгена европейские gateway исключаются; остальные требуют подтверждения VisaRuleEngine.</p>
     </div>}
    </div>
   </article>
   <article className={value.search_wholesalers?'enabled':''}><label className="source-master"><Boxes size={21}/><span><b>Искать у оптовиков / B2B</b><small>HBX, RateHawk, WebBeds, TBO, Dida, HotelX, Expedia</small></span><input type="checkbox" checked={value.search_wholesalers} onChange={e=>set('search_wholesalers',e.target.checked)}/></label><p className="source-description">Отели, чартеры и блоки мест, трансферы, паромы и автобусы собираются в единый расчёт.</p></article>
   <article className={value.search_retail_diy?'enabled':''}><label className="source-master"><ShoppingBag size={21}/><span><b>Искать самостоятельную сборку</b><small>Розничные перелёты, отели и наземный транспорт</small></span><input type="checkbox" checked={value.search_retail_diy} onChange={e=>set('search_retail_diy',e.target.checked)}/></label><p className="source-description">Независимый retail-сценарий с отдельной нормализацией всех обязательных расходов.</p></article>
  </div>
 </section>;
}
