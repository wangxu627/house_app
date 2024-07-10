import json
import asyncio
import datetime
from urllib.parse import urlparse, parse_qs
from collections import Counter

import requests
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

MONGODB_URI = "mongodb://rabbitlbj:wx*123456789@router.wxioi.fun:27017/?retryWrites=true&loadBalanced=false&serverSelectionTimeoutMS=5000&connectTimeoutMS=10000&authSource=admin&authMechanism=SCRAM-SHA-256"
ENTRY_URL = "https://zw.cdzjryb.com/zwdt/SCXX/Default.aspx?action=ucSCXXShowNew"
FLOOR_ESTATE_OF_VIEWS_URL = "https://zw.cdzjryb.com/house-one2one/one2one/getFloorEstateOfViews"
HNO_AND_UNO_URL = "https://zw.cdzjryb.com/house-one2one/one2one/getHnoAndUnos"
JS_URL = "https://zw.cdzjryb.com/roompricezjw/index.html?param=859DC59854A66F4A373D717E6C4599E66FFB261F6371DBF56414EE732C8B3BFEF26B074251750C30C1F4D3507183AE11"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def get_viewstate(soup):
    form = soup.find('form')
    if form:
        first_div = form.find('div')
        if first_div:
            # 查找name为__VIEWSTATE的input标签
            viewstate_input = first_div.find('input', attrs={'name': '__VIEWSTATE'})
            if viewstate_input:
                viewstate_value = viewstate_input.get('value')
                return viewstate_value


def get_floor_estate_of_views(token):
    form_data = {
        "inputStr": token
    }
    response = requests.post(FLOOR_ESTATE_OF_VIEWS_URL, headers=headers, data=form_data)
    response_data = response.json()
    room_status = [room["status"] for floor in response_data["datas"] for room in floor["roomNos"]]
    return room_status


def get_hno_and_unos(token):
    form_data = {
        "inputStr": token
    }
    response = requests.post(HNO_AND_UNO_URL, headers=headers, data=form_data)
    response_data = response.json()
    hno_and_uno = [(uno["HNO"], uno["UNO"]) for floor in response_data["datas"] for uno in floor["UNOLIST"]]
    return hno_and_uno


def get_entry_params(name, excluded_types=["商业", "车位"]):
    response = requests.get(ENTRY_URL, headers=headers)
    if response.status_code == 200:
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        viewstate_value = get_viewstate(soup)
        form_data = {
            'ID_ucSCXXShowNew$txtpName': name,
            '__VIEWSTATE': viewstate_value,
        }
        response = requests.post(ENTRY_URL, headers=headers, data=form_data)
        if response.status_code == 200:
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table', id='ID_ucSCXXShowNew_gridView')
            rows = table.find_all('tr')
            params = []
            for row in rows[1:]:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    number = cells[0].find("input").get('value')
                    type_td_text = cells[4].get_text(strip=True)
                    area = cells[6].get_text(strip=True)
                    release_date = cells[7].get_text(strip=True)
                    second_last_td = cells[-2]
                    link_tag = second_last_td.find('a')
                    if link_tag and type_td_text not in excluded_types:
                        link = link_tag.get('href')
                        parsed_url = urlparse(link)
                        query_params = parsed_url.query
                        params_dict = parse_qs(query_params)
                        param_value = params_dict.get('param', [None])[0]
                        params.append([param_value, number, type_td_text, area, release_date])
            return params
    return []


class AsyncWebReq:
    def __init__(self):
        self.browser = None
        self.page = None
        self.playwright = None

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()
        await self.page.goto(JS_URL)

    async def aes_decrypt(self, param):
        if self.page is None:
            await self.init_browser()
        result = await self.page.evaluate('''(param) => {
            return FuniEncryptionUtil.AES.decrypt(param);
        }''', param)
        return result

    async def floor_token(self, params):
        if self.page is None:
            await self.init_browser()
        result = await self.page.evaluate('''(params) => {
            function getFloorToken(urlParam, hno, uno) {
                let regionCode = '';
                let ids = [];
                let u = '';

                [ids, u, regionCode] = FuniEncryptionUtil.AES.ecbDecrypt(urlParam).split(",")
                ids = [ids]
                regionCode = FuniEncryptionUtil.AES.encrypt(regionCode);
                ids = FuniEncryptionUtil.AES.encrypt(JSON.stringify(ids));
                hno = FuniEncryptionUtil.AES.encrypt(hno);
                uno = FuniEncryptionUtil.AES.encrypt(uno);

                aesResult = FuniEncryptionUtil.AES.encrypt(JSON.stringify({
                    hno: hno,
                    uno: uno,
                    regionCode: regionCode,
                    ids: ids
                }))
                inputStr = FuniEncryptionUtil.xxtea.encrypt(aesResult)
                return inputStr;
            }

            const tokens = [];
            for(const param of params) {
              tokens.push(getFloorToken(param[0], param[1], param[2]));
            }
            return tokens;
        }''', params)
        return result

    async def uno_token(self, params):
        if self.page is None:
            await self.init_browser()
        result = await self.page.evaluate('''(params) => {
            function getUnoToken(urlParam) {
                let regionCode = '';
                let ids = [];
                let u = '';

                [ids, u, regionCode] = FuniEncryptionUtil.AES.ecbDecrypt(urlParam).split(",")
                ids = [ids]
                regionCode = FuniEncryptionUtil.AES.encrypt(regionCode);
                ids = FuniEncryptionUtil.AES.encrypt(JSON.stringify(ids));
                aesResult = FuniEncryptionUtil.AES.encrypt(JSON.stringify({
                    regionCode: regionCode,
                    ids: ids
                }))
                inputStr = FuniEncryptionUtil.xxtea.encrypt(aesResult)
                return inputStr;
            }

            const tokens = [];
            for(const param of params) {
              tokens.push(getUnoToken(param));
            }
            return tokens;
        }''', params)
        return result

    async def close_browser(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


async def get_counter(decryptor, name):
    release_items = get_entry_params(name)
    params = [sublist[0] for sublist in release_items]
    print(release_items)
    tokens = await decryptor.uno_token(params)
    floor_params = []
    for idx, token in enumerate(tokens):
        hno_and_uno = get_hno_and_unos(token)
        for hu in hno_and_uno:
            hno = hu[0]
            uno = hu[1]
            floor_params.append([params[idx], hno, uno, release_items[idx]])

    tokens = await decryptor.floor_token(floor_params)
    total_counter = Counter({})
    for floor, token in zip(floor_params, tokens):
        room_status = get_floor_estate_of_views(token)
        counter = Counter([await decryptor.aes_decrypt(single) for single in room_status])
        print(f'{floor[1]}-{floor[2]}: {counter}')
        total_counter += counter
        insert_mongo_single(name, counter, floor[1], floor[2], floor[3])
    return total_counter


def insert_mongo_single(name, counter, hall_number, unit_number, info):
    from mongoengine import connect, Document, IntField, StringField, DateTimeField, FloatField, DynamicField
    connect(host=MONGODB_URI, db="available_house")

    class SingleCount(Document):
        name = StringField(required=True)

        available_count = IntField()
        sold_count = IntField()
        other_count = IntField()
        counter_info = StringField()
        hall_number = DynamicField()
        unit_number = DynamicField()
        release_number = StringField()
        house_type = StringField()
        area = FloatField()
        release_date = DateTimeField()
        created_date = DateTimeField(default=datetime.datetime.utcnow)

    excluded_elements = {'已售', '可售'}
    available_count = counter["可售"]
    sold_count = counter["已售"]
    other_count = sum(count for item, count in counter.items() if item not in excluded_elements)
    doc = SingleCount(name=name,
                      available_count=available_count,
                      sold_count=sold_count,
                      other_count=other_count,
                      counter_info=json.dumps(counter, ensure_ascii=False),
                      hall_number=hall_number,
                      unit_number=unit_number,
                      release_number=info[1],
                      release_date=info[4],
                      area=info[3],
                      house_type=info[2])
    doc.save()


def insert_mongo_total(name, counter):
    from mongoengine import connect, Document, IntField, StringField, DateTimeField
    connect(host=MONGODB_URI, db="available_house")
    
    class TotalCount(Document):
        name = StringField(required=True)
        available_count = IntField()
        sold_count = IntField()
        other_count = IntField()
        counter_info = StringField()
        created_date = DateTimeField(default=datetime.datetime.utcnow)

    excluded_elements = {'已售', '可售'}
    available_count = counter["可售"]
    sold_count = counter["已售"]
    other_count = sum(count for item, count in counter.items() if item not in excluded_elements)
    doc = TotalCount(name=name, available_count=available_count, sold_count=sold_count,
                     other_count=other_count, counter_info=json.dumps(counter, ensure_ascii=False))
    doc.save()


async def main():
    decryptor = AsyncWebReq()
    await decryptor.init_browser()

    for name in ["保利和颂", "保利天府瑧悦花园", "锦粼观邸", "阅天府", "越秀曦悦府", "人居越秀和樾林语花园", "人居越秀鹿溪樾府小区"]:
        total_counter = await get_counter(decryptor, name)
        insert_mongo_total(name, total_counter)


if __name__ == '__main__':
    asyncio.run(main())
