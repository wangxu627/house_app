from playwright.async_api import async_playwright
import asyncio
from collections import Counter
from urllib.parse import urlparse, parse_qs
import requests
from bs4 import BeautifulSoup

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
            rows = soup.find_all('tr')
            params = []
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    type_td = cells[4]
                    type_td_text = type_td.get_text(strip=True)
                    print(type_td_text)
                    second_last_td = cells[-2]
                    link_tag = second_last_td.find('a')
                    if link_tag and type_td_text not in excluded_types:
                        link = link_tag.get('href')
                        parsed_url = urlparse(link)
                        query_params = parsed_url.query
                        params_dict = parse_qs(query_params)
                        param_value = params_dict.get('param', [None])[0]
                        params.append(param_value)
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
            // 在浏览器上下文中执行的 JavaScript 代码
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



async def main():
    decryptor = AsyncWebReq()
    await decryptor.init_browser()

    name = "保利和颂"
    params = get_entry_params(name)
    tokens = await decryptor.uno_token(params)
    floor_params = []
    for idx, token in enumerate(tokens):
        hno_and_uno = get_hno_and_unos(token)
        for hu in hno_and_uno:
            hno = hu[0]
            uno = hu[1]
            floor_params.append([params[idx], hno, uno])

    tokens = await decryptor.floor_token(floor_params)
    total_counter = Counter({})
    for floor, token in zip(floor_params, tokens):
        room_status = get_floor_estate_of_views(token)
        counter = Counter([await decryptor.aes_decrypt(single) for single in room_status])
        print(f'{floor[1]}-{floor[2]}: {counter}')
        total_counter += counter
    print(total_counter)



if __name__ == '__main__':
    asyncio.run(main())
