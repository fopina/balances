import requests
from common.cli import BasicCLI
from common.cli.fx import CryptoFXMixin

DECIMALS = 1000000


class Client(requests.Session):
    URL = 'https://phoenix-lcd.terra.dev/cosmos/'

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0',
            }
        )

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

    def rewards(self, wallet):
        r = self.get(f'distribution/v1beta1/delegators/{wallet}/rewards')
        r.raise_for_status()
        return r.json()

    def vesting(self, wallet):
        r = self.get(f'auth/v1beta1/accounts/{wallet}')
        r.raise_for_status()
        return r.json()


class CLI(CryptoFXMixin, BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('wallet')

    def handle(self, args):
        hass_data = {
            'state': 0,
            'attributes': {
                'usd': 0,
                'rate': 0,
                'balance': 0,
                'delegated': 0,
                'rewards': 0,
                'vesting': 0,
                'unit_of_measurement': 'LUNA',
            },
        }

        c = Client()
        for d in c.delegations(args.wallet).get('delegation_responses', []):
            hass_data['attributes']['delegated'] += float(d['balance']['amount']) / DECIMALS
        for d in c.balances(args.wallet).get('balances', []):
            hass_data['attributes']['balance'] += float(d['amount']) / DECIMALS
        for d in c.rewards(args.wallet).get('rewards', []):
            for d1 in d.get('reward', []):
                hass_data['attributes']['rewards'] += float(d1['amount']) / DECIMALS
        for d in c.vesting(args.wallet).get('account', {}).get('base_vesting_account', {}).get('original_vesting', []):
            hass_data['attributes']['vesting'] += float(d['amount']) / DECIMALS

        hass_data['state'] = hass_data['attributes']['balance'] + hass_data['attributes']['delegated']
        hass_data['attributes']['rate'] = self.get_crypto_fx_rate('terra-luna-2', coinmarketcap_slugs='terra-luna-v2')
        hass_data['attributes']['usd'] = hass_data['state'] * hass_data['attributes']['rate']
        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI()()
