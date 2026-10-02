import {test,expect} from '@playwright/test';

test('Pages subpath loads its own assets and survives reload',async ({page})=>{
 const broken=[];
 page.on('response',response=>{if(response.url().includes('/trip-optimizer/')&&response.status()>=400)broken.push(`${response.status()} ${response.url()}`)});
 await page.goto('./');
 await expect(page.getByRole('heading',{name:'Ваш отдых. Все варианты.'})).toBeVisible();
 await page.reload();
 await expect(page.getByRole('button',{name:'Найти отдых'})).toBeVisible();
 expect(broken).toEqual([]);
});

test('country picker shows only matching public tours',async ({page})=>{
 await page.goto('./');
 await page.getByLabel('Выбор направления').selectOption('Выбранные страны');
 await page.getByRole('button',{name:'Таиланд',exact:true}).click();
 await expect(page.getByRole('heading',{name:/Таиланд · Паттайя · Olive Tree/})).toBeVisible();
 await expect(page.getByRole('heading',{name:/Турция · Аланья/})).toHaveCount(0);
 await page.getByRole('button',{name:'Подробнее и все расходы'}).first().click();
 await expect(page.getByRole('dialog').getByRole('link',{name:/Предложение и источник цены/})).toHaveAttribute('href',/1001tur\.ru/);
});

test('all sources off blocks empty API search',async ({page})=>{
 let calls=0;
 await page.route('**/api/search',route=>{calls++;return route.fulfill({status:200,contentType:'application/json',body:'{}'})});
 await page.goto('./');
 await page.getByRole('checkbox',{name:/Искать у туроператоров/}).uncheck();
 await page.getByRole('checkbox',{name:/Искать у оптовиков/}).uncheck();
 await page.getByRole('checkbox',{name:/Искать самостоятельную сборку/}).uncheck();
 await expect(page.locator('.error-box[role="alert"]')).toContainText('Включите хотя бы один источник поиска');
 await page.getByRole('button',{name:'Найти отдых'}).click();
 expect(calls).toBe(0);
});

test('changing filters discards an in-flight search response',async ({page})=>{
 await page.route('**/api/search',async route=>{
  await new Promise(resolve=>setTimeout(resolve,400));
  try{await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({message:'STALE_RESULT_MARKER',offers:[],attempted:[],providers:[]})})}catch{}
 });
 await page.goto('./');
 await page.getByRole('button',{name:'Найти отдых'}).click();
 await page.getByLabel('Выбор направления').selectOption('Выбранные страны');
 await page.getByRole('button',{name:'Турция',exact:true}).click();
 await page.waitForTimeout(650);
 await expect(page.getByText('STALE_RESULT_MARKER')).toHaveCount(0);
});

test('split family controls retain three distinct child ages',async ({page})=>{
 await page.goto('./');
 await page.getByRole('button',{name:/Кто едет/}).click();
 await page.locator('#travellers > summary').click();
 await page.getByRole('checkbox',{name:'Возвращаться в разные даты'}).check();
 await expect(page.getByText('Группа A', {exact:true})).toBeVisible();
 await expect(page.getByText('Группа B', {exact:true})).toBeVisible();
 await expect(page.getByRole('spinbutton',{name:'Возраст ребёнка 1'})).toHaveValue('5');
 await expect(page.getByRole('spinbutton',{name:'Возраст ребёнка 2'})).toHaveValue('7');
 await expect(page.getByRole('spinbutton',{name:'Возраст ребёнка 3'})).toHaveValue('9');
});

test('mobile price detail remains inside viewport',async ({page})=>{
 await page.setViewportSize({width:375,height:667});
 await page.goto('./');
 await page.getByRole('button',{name:'Подробнее и все расходы'}).first().click();
 const dialog=page.getByRole('dialog');
 await expect(dialog).toBeVisible();
 const bounds=await dialog.boundingBox();
 expect(bounds.x).toBeGreaterThanOrEqual(0);
 expect(bounds.x+bounds.width).toBeLessThanOrEqual(376);
 await dialog.getByRole('button',{name:'Закрыть'}).click();
 await expect(dialog).not.toBeVisible();
});

for(const [width,height] of [[375,667],[390,844],[768,1024],[1366,768],[1920,1080]]){
 test(`layout fits ${width}×${height}`,async ({page})=>{
  await page.setViewportSize({width,height});
  await page.goto('./');
  await expect(page.getByRole('button',{name:'Найти отдых'})).toBeVisible();
  const sizes=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth}));
  expect(sizes.scroll).toBeLessThanOrEqual(sizes.viewport+1);
 });
}
