import {chromium,expect} from '@playwright/test';

const url=process.env.TRIP_BASE_URL||'https://jedidijedi2023.github.io/trip-optimizer/';
const browser=await chromium.launch();
const page=await browser.newPage();
const audit={url,consoleErrors:[],pageErrors:[],failedRequests:[],failedResponses:[],resources:{},apiSearchStatus:null};
const safeUrl=value=>{try{const parsed=new URL(value);return parsed.origin+parsed.pathname}catch{return 'invalid-url'}};
page.on('console',message=>{if(message.type()==='error')audit.consoleErrors.push({text:message.text().slice(0,250),source:safeUrl(message.location().url||'')})});
page.on('pageerror',error=>audit.pageErrors.push(error.message.slice(0,250)));
page.on('requestfailed',request=>audit.failedRequests.push({url:safeUrl(request.url()),reason:request.failure()?.errorText||'unknown'}));
page.on('response',response=>{
 const type=response.request().resourceType();audit.resources[type]=(audit.resources[type]||0)+1;
 if(response.status()>=400)audit.failedResponses.push({status:response.status(),url:safeUrl(response.url())});
 if(response.url().includes('/api/search'))audit.apiSearchStatus=response.status();
});
try{
 await page.goto(url,{waitUntil:'load',timeout:30000});
 await page.getByText(/каталог сервера/).first().waitFor({state:'visible',timeout:20000});
 await page.getByRole('button',{name:'Демо'}).click();
 await expect(page.getByRole('button',{name:'Демо'})).toHaveClass(/selected/);
 await page.getByRole('button',{name:'Реальный поиск'}).click();
 const searchResponse=page.waitForResponse(response=>response.url().includes('/api/search'),{timeout:50000}).catch(()=>null);
 await page.getByRole('button',{name:'Найти отдых'}).click();
 await searchResponse;
 await page.waitForTimeout(1200);
 console.log(JSON.stringify(audit,null,2));
}finally{await browser.close()}
