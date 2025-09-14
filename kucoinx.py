from dataclasses import dataclass
from kucoin.client import MarketData, User

from common.cli_ng import BasicCLI
import classyclick


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    key: str = classyclick.Argument()
    secret: str = classyclick.Argument()
    passphrase: str = classyclick.Argument()
    exclude_zeros: bool = classyclick.Option(help='Do not report accounts/tokens with 0 balance')


@classyclick.command()
class CLI(BasicCLI, Args):
    def handle(self):
        prices = MarketData().get_fiat_price()
        client = User(self.key, self.secret, self.passphrase)
        accounts = client.get_account_list()

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            },
        }
        accum = {}

        for account in accounts:
            if account['balance'] == '0' and self.exclude_zeros:
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
    CLI.click()
