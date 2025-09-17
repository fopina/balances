#!/usr/bin/env python
"""
Collect balances using https://portfolio.metamask.io/
This allows collecting multiple tokens without knowing contracts in advance for multiple chains.
"""
from collections import defaultdict
from dataclasses import dataclass

import classyclick
import requests

from common.cli_ng import BasicCLI


class Client(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:100.0) Gecko/20100101 Firefox/100.0',
                'Referer': 'https://portfolio.metamask.io/',
            }
        )

    def accounts(self, wallet, networks: list[int] = None):
        if networks:
            networks = ','.join(map(str, networks))
        r = self.get(
            f'https://accounts.api.cx.metamask.io/v2/accounts/{wallet}/balances', params={'networks': networks}
        )
        r.raise_for_status()
        return r.json()

    def prices(self, network: int, token_addresses: list[str], currency='usd', include_market_data=False):
        r = self.get(
            f'https://price.api.cx.metamask.io/v2/chains/{network}/spot-prices',
            params={
                'tokenAddresses': ','.join(token_addresses),
                'vsCurrency': currency,
                'includeMarketData': 'true' if include_market_data else 'false',
            },
        )
        r.raise_for_status()
        return r.json()


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    wallet: str = classyclick.Argument()
    chain_id: list[int] = classyclick.Option('-c', multiple=True, help='Restrict to these chain_ids - default is all')
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
        data = c.accounts(self.wallet, networks=self.chain_id)

        if not self.no_prices:
            per_chain = defaultdict(list)
            for token in data['balances']:
                per_chain[token['chainId']].append(token['address'])
            prices = {}
            for k, v in per_chain.items():
                price_data = c.prices(k, v)
                for kk, vv in price_data.items():
                    prices[(k, kk)] = vv['usd']
        else:
            prices = {}

        total = 0.0
        for token_balance in data['balances']:
            _s = token_balance['symbol'].lower()
            hass_data['attributes'][f'{_s}_amt'] = token_balance['balance']
            k = (token_balance['chainId'], token_balance['address'])
            if k in prices:
                price = prices[k] * float(token_balance['balance'])
                hass_data['attributes'][f'{_s}_val'] = price
                total += price

        hass_data['state'] = price

        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI.click()
