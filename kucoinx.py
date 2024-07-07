from kucoin.client import MarketData, User

from common.cli import BasicCLI


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('key')
        parser.add_argument('secret')
        parser.add_argument('passphrase')
        parser.add_argument('--exclude-zeros', action='store_true', help='Do not report accounts/tokens with 0 balance')

    def handle(self, args):
        prices = MarketData().get_fiat_price()
        client = User(args.key, args.secret, args.passphrase)
        accounts = client.get_account_list()

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            },
        }
        accum = {}

        for account in accounts:
            if account['balance'] == '0' and args.exclude_zeros:
                continue
            accum[account['currency']] = float(accum.get(account['currency'], 0)) + float(account['balance'])

        subs = client._request('GET', '/api/v1/sub-accounts')
        accum_sub = {}
        for sub in subs:
            for k in ('mainAccounts', 'tradeAccounts', 'marginAccounts'):
                for account in sub[k]:
                    kn = account['currency']
                    kv = float(account['balance'])
                    accum[kn] = float(accum.get(kn, 0)) + kv
                    price = float(prices.get(kn, 0))
                    accum_sub[sub['subName']] = accum_sub.get(sub['subName'], 0) + price * kv

        for k, v in accum.items():
            price = float(prices.get(k, 0))
            k = k.lower()
            usd = price * float(v)
            print(k, v, usd)
            hass_data['state'] += usd
            hass_data['attributes'][k] = v
            hass_data['attributes'][f'{k}_val'] = usd

        for k, v in accum_sub.items():
            k = f'sub_{k}'
            print(k, v)
            hass_data['attributes'][k] = v

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
