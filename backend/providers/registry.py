"""Operational status and price reality, not just marketing API availability.

`connected` is computed live from the backend's own environment variables —
it reflects whether *this* deployment has been given credentials for that
provider, never whether the provider itself is reachable in general.
"""
import os
from backend.models.domain import Access,Reality

def _bool(*names):
    return all(os.getenv(n) for n in names)

def provider_registry():
    records=[
      # name, access, reality, bookable, note, docs_url, connected(), env_hint, wired_into_main_search
      ('Tourvisor',Access.REGISTRATION_REQUIRED,Reality.UNKNOWN,None,'Trial: 300 requests/day, own JWT required','https://api.tourvisor.ru/search/docs',
        _bool('TOURVISOR_TOKEN') and os.getenv('TOURVISOR_ACCESS_MODE')=='trial','TOURVISOR_TOKEN, TOURVISOR_ACCESS_MODE=trial','Проверьте во вкладке «API тест»; в общий поиск пока не включён (нужны справочники departureId/countryId)'),
      ('Hotelbeds / HBX',Access.REGISTRATION_REQUIRED,Reality.SYNTHETIC,False,'Evaluation at api.test.hotelbeds.com; own key/secret required','https://developer.hotelbeds.com/documentation/getting-started/',
        _bool('HOTELBEDS_API_KEY','HOTELBEDS_SECRET'),'HOTELBEDS_API_KEY, HOTELBEDS_SECRET','Проверьте во вкладке «API тест» (нужны конкретные коды отелей); в общий поиск пока не включён'),
      ('DidaTravel rates',Access.REGISTRATION_REQUIRED,Reality.UNKNOWN,None,'Shared PriceSearch test account retired; dedicated sandbox account required','https://apidoc.didatravel.com/booking-api/price-search.html',
        _bool('DIDA_CLIENT_ID','DIDA_LICENSE_KEY') and os.getenv('DIDA_ENVIRONMENT')=='sandbox','DIDA_CLIENT_ID, DIDA_LICENSE_KEY, DIDA_ENVIRONMENT=sandbox','Контент доступен; нормализация тарифов ждёт подтверждённого ответа поставщика'),
      ('DidaTravel content',Access.SANDBOX,Reality.UNKNOWN,False,'Official public test country dictionary returned HTTP 200; no rates','https://apidoc.didatravel.com/content-api-v2/how-to-use-content-api.html',
        True,'—','Работает уже сейчас, ключ не требуется (официальный публичный test-аккаунт)'),
      ('Travelgate HOTELTEST',Access.DEMO,Reality.SYNTHETIC,False,'Official public demo, HOTELTEST access 2, hotels ES284122 and BR1518; test rates only','https://docs.travelgate.com/docs/apis/for-buyers/hotel-x-pull-buyers-api/quickstart/',
        True,'—','Работает уже сейчас в «Реальном поиске» и «API тест», ключ не требуется (официальный публичный demo)'),
      ('Duffel',Access.REGISTRATION_REQUIRED,Reality.SYNTHETIC,False,'Only own duffel_test_ token accepted','https://duffel.com/docs/api/overview/test-mode',
        bool((os.getenv('DUFFEL_TOKEN') or '').startswith('duffel_test_')),'DUFFEL_TOKEN=duffel_test_…','Проверьте во вкладке «API тест» (нужны конкретные аэропорты вылета/прилёта); в общий поиск пока не включён'),
      ('Amadeus',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Self-Service deprecated, official repository archived 2026-07-17; mock fallback','https://github.com/amadeus4dev/developer-guides',
        False,'—','Коммерческий доступ у поставщика недоступен; интеграция не подключена'),
      ('Expedia Rapid',Access.REGISTRATION_REQUIRED,Reality.SYNTHETIC,False,'Partner onboarding then test.ean.com; no credentials supplied','https://developers.expediagroup.com/rapid/setup',
        False,'EXPEDIA_RAPID_API_KEY (партнёрский onboarding)','Требуется партнёрская регистрация у Expedia; адаптер ещё не написан'),
      ('RateHawk',Access.REGISTRATION_REQUIRED,Reality.UNKNOWN,None,'Registration and certification; mock fallback','https://www.ratehawk.com/lp/en/API/',
        _bool('RATEHAWK_SANDBOX_KEY_ID','RATEHAWK_SANDBOX_KEY'),'RATEHAWK_SANDBOX_KEY_ID, RATEHAWK_SANDBOX_KEY','Уже включён в «Реальный поиск» и «API тест» — начнёт возвращать тарифы сразу после регистрации'),
      ('WebBeds',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Commercial/technical onboarding; mock fallback','https://www.webbeds.com/buyers/support/',
        False,'—','Коммерческий договор; адаптер ещё не написан'),
      ('TBO',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Dedicated onboarding; mock fallback','https://demo.tbo.com/tbo-api',
        False,'—','Коммерческий договор; адаптер ещё не написан'),
      ('AviaCenter',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Public XML offered, authorized wire specification required; mock fallback','https://aviacenter.ru/partnering/charters/',
        False,'—','Нужна авторизованная спецификация от поставщика; адаптер ещё не написан'),
      ('SAMO',Access.DEMO,Reality.UNKNOWN,False,'Official UI demo login accepted with the user-authorized historical demo account; API access still contract-gated','https://demo.samo.ru/samotour/',
        False,'—','Только UI-демо; API-доступ отдельно контрактный'),
      ('Juniper',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Public XML docs/WSDL; seller agreement and own UAT credentials required','https://api-edocs.ejuniper.com/',
        False,'—','Нужен агентский договор; адаптер ещё не написан'),
      ('Traveltek',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Public JSON 2.1 quickstart; own test login and current HTTPS contract required','https://traveltek.atlassian.net/wiki/spaces/KNOW/pages/1665236993/Quick%2Bstart%2BJSON%2B2.1%2BAPI',
        False,'—','Нужен контракт и тестовый логин; адаптер ещё не написан'),
      ('Peakwork',Access.COMMERCIAL_CONTRACT_REQUIRED,Reality.UNKNOWN,None,'Documentation access through Peakwork contact; local mock only','https://www.peakwork.com/documentation/',
        False,'—','Доступ к документации по запросу; адаптер ещё не написан'),
      ('Local fixtures',Access.MOCK,Reality.SYNTHETIC,False,'Deterministic mock flights, hotels, packages and family routes','local:fixtures',
        True,'—','Всегда доступны как запасной демонстрационный вариант'),
      ('Open-Meteo',Access.LIVE,Reality.UNKNOWN,False,'Public noncommercial weather only, not prices','https://open-meteo.com/en/docs',
        True,'—','Работает уже сейчас, ключ не требуется'),
      ('Level.Travel public prices',Access.DEEPLINK,Reality.LIMITED_REAL,None,'Dated public-page observations, not family quotes or refreshed availability','https://level.travel/explore/Moscow-Russia/Egypt/october',
        True,'—','Открытые данные, показаны во вкладке «Открытые источники»'),
      ('Aviasales public prices',Access.DEEPLINK,Reality.LIMITED_REAL,None,'Public route-page cached prices; one-way, passenger/baggage conditions unconfirmed','https://www.aviasales.ru/routes/mow/ist',
        True,'—','Открытые данные, показаны во вкладке «Открытые источники»'),
    ]
    return [{'provider':n,'access_status':a,'pricing_reality':p,'bookable':b,'note':note,'source_url':url,
             'connected':connected,'env_hint':env_hint,'integration_note':integration_note}
            for n,a,p,b,note,url,connected,env_hint,integration_note in records]
