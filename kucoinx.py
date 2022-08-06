from kucoin.client import User, MarketData

from common.cli import BasicCLI


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('key')
        parser.add_argument('secret')
        parser.add_argument('passphrase')
    
    def handle(self, args):
        prices = MarketData().get_fiat_price()
        client = User(args.key, args.secret, args.passphrase)
        wallets = client.get_account_list()

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            }
        }
        accum = {}

        for wallet in wallets:
            accum[wallet['currency']] = float(accum.get(wallet['currency'], 0)) + float(wallet['balance'])
        
        for k, v in accum.items():
            price = float(prices.get(k, 0))
            usd = price*float(v)
            print(k, v, usd)
            hass_data['state'] += usd
            hass_data['attributes'][k.lower()] = v
            hass_data['attributes'][f'{k.lower()}_val'] = usd

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
