from datetime import datetime,timezone
from decimal import Decimal
import xml.etree.ElementTree as ET
from backend.providers.http import http

async def cbr_reference_rates():
    result=await http.request('cbr','GET','https://www.cbr.ru/scripts/XML_daily.asp',ttl=3600)
    root=ET.fromstring(result['response'])
    rates={'RUB':Decimal('1')}
    for row in root.findall('Valute'):
        rates[row.findtext('CharCode')]=Decimal(row.findtext('Value').replace(',','.'))/Decimal(row.findtext('Nominal'))
    return {'source':'Bank of Russia reference rate; not card settlement rate','source_url':'https://www.cbr.ru/scripts/XML_daily.asp',
      'fx_date':root.attrib['Date'],'fetched_at':result['fetched_at'],'rub_per_unit':{k:str(v) for k,v in rates.items()},'payment_fees_included':False}
