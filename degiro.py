import requests

from common.cli import BasicCLI, otp


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = 'https://trader.degiro.nl/'

    def __init__(self):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0'
        })
        self._session_id = None
        self._config = None

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def login(self, username, password, otp=None, pin_code=None):
        data = {'username': username, 'password': password}
        path = 'login/secure/login'
        if otp:
            data['oneTimePassword'] = int(otp())
            path = 'login/secure/login/totp'
        elif pin_code:
            data = {
                'username': username,
                'deviceId': password,
                'isBiometricLogin': True,
                'passCode': pin_code,
            }
            path = 'login/secure/login/device'

        r = self.post(path, json=data)
        d = r.json()
        if d['status'] == 0:
            # success
            self._session = d['sessionId']
        elif d['status'] == 3:
            raise ClientError('invalid login/otp')
        elif d['status'] == 6:
            # otpNeeded - required
            raise ClientError('either otp or otp_secret are required')
        else:
            raise ClientError('unexpected status', d)
        self._session_id = d['sessionId']
    
    def get_config(self):
        r = self.get('pa/secure/client', params={'sessionId': self._session_id})
        r.raise_for_status()
        self._config = r.json()['data']
        return self._config

    def get_portfolio(self):
        r = self.get(f'trading/secure/v5/update/{self._config["intAccount"]};jsessionid={self._session_id}', params={'portfolio': 0})
        r.raise_for_status()
        portfolio = []
        for j in r.json()['portfolio']['value']:
            data = {}
            for jj in j['value']:
                if jj['name'] in data:
                    raise Exception('dup', jj['name'])
                data[jj['name']] = jj.get('value')
            portfolio.append(data)
        return portfolio
    
    def product_search(self, ids):
        r = self.post(f'product_search/secure/v5/products/info?intAccount={self._config["intAccount"]}', params={'sessionId': self._session_id}, json=ids)
        r.raise_for_status()
        return r.json()['data']

    def vwd_client(self):
        c = VWDClient()
        c.login(self._config['id'])
        return c


class VWDClient(Client):
    URL = 'https://degiro.quotecast.vwdservices.com/CORS/'

    def __init__(self):
        super().__init__()
        self.headers.update({'Origin': 'https://trader.degiro.nl'})

    def login(self, user_token):
        r = self.post(
            'request_session',
            params={
                'version': '1.0.20201211',
                'userToken': user_token,
            },
            data=b'{"referrer":"https://trader.degiro.nl"}',
        )
        r.raise_for_status()
        d = r.json()
        self._session_id = d['sessionId']
        return self._session_id

    def set_up(self, reqs):
        data = ''.join(f'req({x});' for x in reqs)
        r = self.post(
            self._session_id,
            data=f'{{"controlData":"{data}"}}',
        )
        r.raise_for_status()
        return r.text == ''

    def updates(self):
        r = self.get(self._session_id)
        r.raise_for_status()
        d = r.json()
        req_key_map = {
            x['v'][1]: x['v'][0]
            for x in d
            if x['m'] == 'a_req'
        }
        r = {
            req_key_map[x['v'][0]]: x['v'][1]
            for x in d
            if x['m'] == 'un'
        }
        return r


class CLI(otp.OTPMixin, BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('username')
        parser.add_argument('password')
        parser.add_argument('-p', '--pin', help='use device login with this pin code (password should be device id)')

    def handle(self, args):
        client = Client()

        client.login(args.username, args.password, otp=self.otp_holder(args), pin_code=args.pin)
        client.get_config()

        portfolio = client.get_portfolio()
        ids = [x['id'] for x in portfolio]
        prod_info = client.product_search(ids)
        for x in portfolio:
            x['product'] = prod_info[x['id']]

        products = {}
        vwd_ids = {}

        # update PRODUCTs with product info
        for x in portfolio:
            if x['positionType'] != 'PRODUCT':
                continue
            key = f"{x['product']['symbol']}_{x['product']['productType']}".lower()
            keyv = f'{key}_val'
            products[key] = products.get(key, 0) + x['size']
            products[keyv] = products.get(keyv, 0) + x['value']
            if x['size'] > 0:
                vwd_ids[f"{x['product']['vwdId']}.LastPrice"] = key

        # update CASH with product info
        for x in portfolio:
            if x['positionType'] != 'CASH':
                continue
            if x['id'] in ('FLATEX_EUR', 'FLATEX_USD'):
                key = f"{x['id']}".lower()
                keyv = f'{key}_val'
                products[key] = products.get(key, 0) + x['size']
                products[keyv] = products.get(keyv, 0) + x['value']

        # update PRODUCT values with VWD real time data
        vclient = client.vwd_client()
        assert vclient.set_up(vwd_ids.keys()) == True
        for upk, upv in vclient.updates().items():
            key = vwd_ids[upk]
            products[f'{key}_val'] = products[key] * upv

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'EUR',
            }
        }

        for k, v in products.items():
            print(f"{k}: {v}")
            hass_data['attributes'][k] = v
            hass_data['state'] += v

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
