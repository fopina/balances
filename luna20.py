import requests

from common.cli import BasicCLI


class Client(requests.Session):
    URL = 'https://phoenix-lcd.terra.dev/cosmos/'

    def __init__(self):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0',
        })

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def delegations(self, wallet):
        r = self.get(f'staking/v1beta1/delegations/{wallet}', params={'pagination.limit': '999'})
        r.raise_for_status()
        return r.json()

    def balances(self, wallet):
        r = self.get(f'bank/v1beta1/balances/{wallet}')
        r.raise_for_status()
        return r.json()

    def usd_rate(self):
        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=terra-luna-2&vs_currencies=usd')
        r.raise_for_status()
        return r.json()['terra-luna-2']['usd']


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('wallet')
    
    def handle(self, args):
        hass_data = {
            'state': 0,
            'attributes': {
                'usd': 0,
                'rate': 0,
                'vested': 0,
                'vesting': 0,
                'unit_of_measurement': 'LUNA',
            }
        }

        c = Client()

        for d in c.delegations(args.wallet).get('delegation_responses', []):
            hass_data['attributes']['vesting'] += float(d['balance']['amount']) / 1000000
        for d in c.balances(args.wallet).get('balances', []):
            hass_data['attributes']['vested'] += float(d['amount']) / 1000000

        hass_data['state'] = hass_data['attributes']['vested'] + hass_data['attributes']['vesting']
        hass_data['attributes']['rate'] = c.usd_rate()
        hass_data['attributes']['usd'] = hass_data['state'] * hass_data['attributes']['rate']
        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI()()
