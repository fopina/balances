from functools import cached_property
import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware

from common.cli import BasicCLI


CONTRACT_RACE = '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0'
CONTRACT_SLIME = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'
CONTRACT_SNAILNFT = '0xec675B7C5471c67E9B203c6D1C604df28A89FB7f'

ABI_RACE = [
    {
        "inputs": [],
        "name": "claimableRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]
ABI_ACCOUNT = [
    {
        'inputs': [{'internalType': 'address', 'name': 'account', 'type': 'address'}],
        'name': 'balanceOf',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    }
]


class Client:
    def __init__(
        self,
        wallet,
        web3_provider,
        web3_provider_class=None,
    ):
        if web3_provider_class is None:
            web3_provider_class = Web3.HTTPProvider
        self.web3 = Web3(web3_provider_class(web3_provider))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.wallet = wallet

    @cached_property
    def race_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_RACE), abi=ABI_RACE)

    @cached_property
    def slime_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SLIME), abi=ABI_ACCOUNT)

    @cached_property
    def snailnft_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_SNAILNFT), abi=ABI_ACCOUNT)

    def claimable_rewards(self):
        return self.race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_slime(self):
        return self.slime_contract.functions.balanceOf(self.wallet).call({'from': self.wallet}) / 1000000000000000000

    def balance_of_snails(self):
        return self.snailnft_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})

    def get_balance(self):
        return self.web3.eth.get_balance(self.wallet) / 1000000000000000000


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('wallet')
        parser.add_argument('--web3', default='https://api.avax.network/ext/bc/C/rpc', help='WEB3 Provider HTTP')
        parser.add_argument('-k', '--ignore-ssl', action='store_true', help='Disable TLS verification')
    
    def handle(self, args):
        client = Client(args.wallet, args.web3)

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            }
        }

        r = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=snail-trail,avalanche-2&vs_currencies=usd')
        r.raise_for_status()
        r = r.json()

        hass_data['attributes']['avax'] = client.get_balance()
        hass_data['attributes']['unclaimed'] = client.claimable_rewards()
        hass_data['attributes']['claimed'] = client.balance_of_slime()
        hass_data['attributes']['snails'] = client.balance_of_snails()
        hass_data['attributes']['claimed'] = client.balance_of_slime()
        hass_data['attributes']['slime_rate'] = r['snail-trail']['usd']
        hass_data['attributes']['avax_rate'] = r['avalanche-2']['usd']
        hass_data['attributes']['avax_slime'] = r['avalanche-2']['usd'] / r['snail-trail']['usd']
        hass_data['state'] = (hass_data['attributes']['unclaimed'] + hass_data['attributes']['claimed']) * hass_data['attributes']['slime_rate'] + hass_data['attributes']['avax'] * hass_data['attributes']['avax_rate']

        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI()()
