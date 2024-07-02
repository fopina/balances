import requests
import re

from common.cli import BasicCLI


TAG_RE = re.compile(r'<.+?>')


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = 'https://aforronet.igcp.pt/'

    def __init__(self) -> None:
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
                'Referer': self.URL,
            }
        )

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def login(self, username, password, nif):
        r = self.get('Iimf.AforroNet.UI/services/login/Login.aspx')
        r.raise_for_status()

        data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'txtIdentificacao': username,
            'txtSenha': password,
            'btLoginAfr.x': "0",
            'btLoginAfr.y': "0",
        }

        m = re.findall(r'Indique o <strong>(\d+).*</strong> e <strong>(\d+).*</strong>', r.text)
        if not m:
            raise ClientError('NIF positions not found')
        pos = list(map(lambda x: nif[int(x) - 1], m[0]))
        data['dlPrim_Pos'] = pos[0]
        data['dlSeg_Pos'] = pos[1]

        m = re.findall(r'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="(.*?)" />', r.text)
        if not m:
            raise ClientError('__VIEWSTATE not found')
        data['__VIEWSTATE'] = m[0]

        m = re.findall(
            r'<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*?)" />', r.text
        )
        if not m:
            raise ClientError('__VIEWSTATEGENERATOR not found')
        data['__VIEWSTATEGENERATOR'] = m[0]

        m = re.findall(r'<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*?)" />', r.text)
        if not m:
            raise ClientError('__EVENTVALIDATION not found')
        data['__EVENTVALIDATION'] = m[0]

        r = self.post('Iimf.AforroNet.UI/services/login/Login.aspx', data=data)
        r.raise_for_status()
        if r.url.endswith('/Iimf.AforroNet.UI/services/login/Login.aspx'):
            msg = re.findall(
                r'''<TD class='msgCustomValSumm' id='MessageCustomValSumm' .*?><div id="CValSummary">(.*?)</div></TD>''',
                r.text,
                re.DOTALL,
            )
            if msg:
                msg = msg[0]
                msg = TAG_RE.sub(' ', msg)
                msg = re.sub(r'\s\s+', '\n', msg)
                msg = '; '.join(msg.strip().splitlines())
            raise ClientError(msg)

    def daily_statement(self):
        r = self.get('Iimf.AforroNet.UI/services/Consulta/Saldo.aspx')
        r.raise_for_status()
        subs = []
        panels = re.findall(r'<div id="(panel\d+)">(.*?)</div>', r.text, re.DOTALL)
        for panel in panels:
            m_tr = re.findall(r'<tr.*?>(.*?)</tr>', panel[1], re.DOTALL)
            for d_tr in m_tr:
                sub = list(re.findall(r'<td.+?>(.*?)</td>', d_tr, re.DOTALL))
                series = TAG_RE.sub('', sub[0])
                if len(sub) != 5:
                    # subtotal
                    assert 'SubTotal:' in sub[0]
                    continue

                sub.append(series)
                for j in range(2, 5):
                    sub[j] = float(sub[j].replace(',', '.').replace('\xa0', ''))
                subs.append(sub)
        return subs


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('username')
        parser.add_argument('password')
        parser.add_argument('nif')

    def handle(self, args):
        client = Client()
        if args.insecure:
            client.verify = False
        client.login(args.username, args.password, args.nif)
        subs = client.daily_statement()

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'EUR',
            },
        }

        print('Subscriptions:')
        for sub in subs:
            _n = sub[1]
            hass_data['attributes'][f'{_n}_series'] = sub[5]
            hass_data['attributes'][f'{_n}_date'] = sub[0]
            hass_data['attributes'][f'{_n}_unitprice'] = sub[2]
            hass_data['attributes'][f'{_n}_units'] = sub[3]
            hass_data['attributes'][f'{_n}_value'] = sub[4]
            hass_data['state'] += sub[4]
            print(f"* {sub[1]}: {sub[0]} {sub[2:]}")
        print(f"Total: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
