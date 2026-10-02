import test from 'node:test';
import assert from 'node:assert/strict';
import {addDays,defaults,defaultParty,defaultSearchSourceSettings,searchMock,selectedCountryCodes,sourcesEnabled,validate,validIsoDate} from '../lib/search.ts';

const tomorrow=addDays(new Date().toLocaleDateString('sv-SE'),1);
const filters=(changes={})=>({...defaults,earliest:tomorrow,latestDeparture:addDays(tomorrow,2),latest:addDays(tomorrow,25),destinationMode:'Выбранные страны',destinations:'TR',budget:1500000,...changes});
const sources=(changes={})=>({...defaultSearchSourceSettings,...changes});

test('a search with every source disabled is rejected before generating offers',()=>{
 const disabled=sources({search_tour_operators:false,search_wholesalers:false,search_retail_diy:false});
 assert.equal(sourcesEnabled(disabled),false);
 assert.match(validate(filters(),defaultParty,disabled).join(' '),/Включите хотя бы один источник/);
 assert.deepEqual(searchMock(filters(),defaultParty,disabled).offers,[]);
});

test('operator master switch without any child source does not count as enabled',()=>{
 const disabled=sources({search_russian_operators:false,search_foreign_operators:false,search_wholesalers:false,search_retail_diy:false});
 assert.equal(sourcesEnabled(disabled),false);
});

test('foreign operator remains selectable without a positioning flight',()=>{
 const onlyForeign=sources({search_russian_operators:false,search_wholesalers:false,search_retail_diy:false,allow_foreign_package_positioning:false});
 const result=searchMock(filters(),defaultParty,onlyForeign);
 assert.equal(result.errors.length,0);
 assert.ok(result.offers.length>0);
 assert.ok(result.offers.every(o=>o.kind==='foreign'&&o.gateway===''&&o.access_status==='MOCK'&&o.pricing_reality==='SYNTHETIC'&&o.savings===null));
});

test('source combinations constrain demonstration offer kinds',()=>{
 const cases=[
  [sources({search_wholesalers:false,search_retail_diy:false}),new Set(['russian','foreign','gatewayPackage'])],
  [sources({search_tour_operators:false,search_retail_diy:false}),new Set(['wholesale','charter'])],
  [sources({search_tour_operators:false,search_wholesalers:false}),new Set(['diy'])],
  [sources({search_tour_operators:false}),new Set(['wholesale','charter','diy'])],
 ];
 for(const [settings,allowed] of cases){
  const result=searchMock(filters(),defaultParty,settings);
  assert.equal(result.errors.length,0);
  assert.ok(result.offers.length>0);
  assert.ok(result.offers.every(o=>allowed.has(o.kind)));
 }
});

test('selected countries are respected by demo results',()=>{
 const result=searchMock(filters({destinations:'Таиланд'}),defaultParty);
 assert.deepEqual(selectedCountryCodes(filters({destinations:'Таиланд'})),['TH']);
 assert.ok(result.offers.every(o=>o.code==='TH'));
});

test('invalid calendar dates and reversed window are rejected',()=>{
 assert.equal(validIsoDate('2026-02-30'),false);
 assert.match(validate(filters({earliest:'2026-02-30'}),defaultParty).join(' '),/корректные даты/);
 assert.match(validate(filters({latest:addDays(tomorrow,-1)}),defaultParty).join(' '),/порядок дат/);
 assert.match(validate(filters({earliest:'2026-01-01',latestDeparture:'2026-01-02',latest:'2026-01-20'}),defaultParty).join(' '),/будущих дат/);
});

test('split family keeps one outbound and separate group returns',()=>{
 const party={...defaultParty,split:true};
 const result=searchMock(filters(),party,sources({search_wholesalers:false,search_retail_diy:false,search_foreign_operators:false}));
 assert.ok(result.offers.length>0);
 for(const offer of result.offers){
  assert.deepEqual(offer.nights,[9,18]);
  assert.equal(offer.returns.length,2);
  assert.equal(offer.people,5);
  assert.equal(offer.savings,null);
  assert.equal(offer.costs.filter(c=>/Перелёты туда и обратно|Пакет: перелёт и проживание/.test(c.label)).length,1);
 }
});

test('without Schengen no demonstration route enters FRA gateway',()=>{
 const result=searchMock(filters({schengen:false}),defaultParty);
 assert.ok(result.offers.every(o=>o.gatewayCountry!=='DE'));
});

test('date arithmetic crosses the year boundary without losing a night',()=>{
 assert.equal(addDays('2026-12-31',1),'2027-01-01');
 assert.equal(addDays('2026-12-31',9),'2027-01-09');
});
