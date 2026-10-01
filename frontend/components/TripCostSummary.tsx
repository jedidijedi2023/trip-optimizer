import {money} from '@/lib/search';
import {calculationSummary,quoteIncluded,observationValid,type TripCalculation} from '@/lib/trip-quotes';
export default function TripCostSummary({calculation}:{calculation?:TripCalculation}){
 const s=calculationSummary(calculation);
 return <section className="quote-total sourced-costs" aria-live="polite"><h3>Стоимость по найденным предложениям</h3>
 <p>Все суммы в RUB за указанных гостей и весь срок. Неизвестные расходы не заменяются демо-ценами.</p>
 {calculation&&<div className="cost-table">{calculation.rows.map(r=>{const q=calculation.quotes[r.id],has=quoteIncluded(q,r.queryKey),pending=observationValid(q,r.queryKey);return <div key={r.id}><span>{r.label}{has&&<small className="price-source"><a href={q.sourceUrl} target="_blank" rel="noopener noreferrer">Источник ↗</a> · {new Date(q.observedAt).toLocaleString('ru-RU')}<br/>{q.description}<br/>{pending?'Наблюдаемая цена; тариф и соответствие условиям ещё не подтверждены':'Параметры подтверждены вами'}</small>}</span><strong>{has?money(q.amount):'Не найдена'}</strong></div>;})}</div>}
 <h4>{s.complete?'Полная стоимость поездки':'Сумма найденных составляющих'}</h4><strong>{s.known?money(s.total):'Стоимость не определена'}</strong>
 <p>{s.complete?'Все расходы заполнены. Повторно проверьте цены и доступность перед покупкой.':'Полная стоимость пока не определена.'}</p>
 {s.unknown>0&&<p>Неизвестных расходов: {s.unknown}.</p>}{s.pending>0&&<p>Цен, требующих проверки тарифа: {s.pending}. Минимум выдачи может не включать нужный багаж или подходящий маршрут.</p>}
 {calculation&&!calculation.parametersValid&&<p role="alert">Исправьте даты, маршрут или размещение гостей.</p>}
 </section>;
}
