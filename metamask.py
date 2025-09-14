#!/usr/bin/env python
"""
Collect balances using https://portfolio.metamask.io/
This allows collecting multiple tokens without knowing contracts in advance for multiple chains.
"""
import requests

from common.cli_ng import BasicCLI
import classyclick
from dataclasses import dataclass


class Client(requests.Session):
    URL = 'https://account.metafi.codefi.network/'

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0',
                'Referer': 'https://portfolio.metamask.io/',
            }
        )

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def accounts(self, wallet, chain_id, include_prices=True):
        r = self.get(f'accounts/{wallet}', params={'chainId': chain_id, 'includePrices': include_prices})
        r.raise_for_status()
        return r.json()


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    wallet: str = classyclick.Argument()
    chain_id: int = classyclick.Argument()
    no_prices: bool = classyclick.Option(help='Do not include prices for the tokens')


@classyclick.command()
class CLI(BasicCLI, Args):
    def handle(self):
        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            },
        }

        c = Client()
        data = c.accounts(self.wallet, self.chain_id, include_prices=not self.no_prices)

        print(f'Data updated at: {data["updatedAt"]}')
        _s = data['nativeBalance']['symbol'].lower()
        hass_data['attributes'][f'{_s}_amt'] = data['nativeBalance']['balance']
        hass_data['attributes'][f'{_s}_val'] = data['nativeBalance']['value']['marketValue']

        for token_balance in data['tokenBalances']:
            _s = token_balance['symbol'].lower()
            hass_data['attributes'][f'{_s}_amt'] = token_balance['balance']
            hass_data['attributes'][f'{_s}_val'] = token_balance['value']['marketValue']

        hass_data['state'] = data['value']['marketValue']

        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI.click()
