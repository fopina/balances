from functools import cached_property
from web3 import Web3
from web3.middleware import geth_poa_middleware
from requests.exceptions import HTTPError

from common.cli import BasicCLI, fx, hass


CONTRACT_RACE = '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0'
CONTRACT_SLIME = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'
CONTRACT_SNAILNFT = '0xec675B7C5471c67E9B203c6D1C604df28A89FB7f'
CONTRACT_MEGA_RACE = '0xa65592fC7afa222Ac30a80F273280e6477a274e3'
CONTRACT_WAVAX = '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'

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

    @cached_property
    def wavax_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_WAVAX), abi=ABI_ACCOUNT)

    @cached_property
    def mega_race_contract(self):
        return self.web3.eth.contract(address=self.web3.toChecksumAddress(CONTRACT_MEGA_RACE), abi=ABI_RACE)

    def claimable_slime(self):
        return self.race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_slime(self):
        return self.slime_contract.functions.balanceOf(self.wallet).call({'from': self.wallet}) / 1000000000000000000

    def claimable_wavax(self):
        return self.mega_race_contract.functions.claimableRewards().call({'from': self.wallet}) / 1000000000000000000

    def balance_of_wavax(self, raw=False):
        x = self.wavax_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})
        if raw:
            return x
        return x / 1000000000000000000

    def balance_of_snails(self):
        return self.snailnft_contract.functions.balanceOf(self.wallet).call({'from': self.wallet})

    def get_balance(self):
        return self.web3.eth.get_balance(self.wallet) / 1000000000000000000


class CLI(fx.CryptoFXMixin, BasicCLI):
    def default_parser(self, parser):
        parser.add_argument(
            '--hass', nargs='+', help='URL(s) to push the data to HASS - ONE FOR EACH WALLET SPECIFIED, SAME ORDER'
        )
        parser.add_argument('--hass-token', help='Token to push to HASS')

    def extend_parser(self, parser):
        parser.add_argument('wallet', nargs='+')
        parser.add_argument('--web3', default='https://api.avax.network/ext/bc/C/rpc', help='WEB3 Provider HTTP')
        parser.add_argument('-k', '--ignore-ssl', action='store_true', help='Disable TLS verification')

    def handle(self, args):
        if args.hass:
            assert args.hass_token is not None
            assert len(args.hass) == len(args.wallet)

        rates = self.get_crypto_fx_rate(
            ['snail-trail', 'avalanche-2'],
            coinmarketcap_slugs={
                'snail-trail': 'snail-trail',
                'avalanche-2': 'avalanche',
            },
        )

        r = []
        for wallet in args.wallet:
            client = Client(wallet, args.web3)

            hass_data = {
                'state': 0,
                'attributes': {
                    'unit_of_measurement': 'USD',
                },
            }

            hass_data['attributes']['avax'] = client.get_balance()
            hass_data['attributes']['unclaimed'] = client.claimable_slime()
            hass_data['attributes']['claimed'] = client.balance_of_slime()
            hass_data['attributes']['unclaimedw'] = client.claimable_wavax()
            hass_data['attributes']['wavax'] = client.balance_of_wavax()
            hass_data['attributes']['snails'] = client.balance_of_snails()
            hass_data['attributes']['claimed'] = client.balance_of_slime()
            hass_data['attributes']['slime_rate'] = rates['snail-trail']
            hass_data['attributes']['avax_rate'] = rates['avalanche-2']
            hass_data['attributes']['avax_slime'] = rates['avalanche-2'] / rates['snail-trail']
            hass_data['state'] = (
                hass_data['attributes']['unclaimed'] + hass_data['attributes']['claimed']
            ) * hass_data['attributes']['slime_rate'] + (
                hass_data['attributes']['avax']
                + hass_data['attributes']['unclaimedw']
                + hass_data['attributes']['wavax']
            ) * hass_data[
                'attributes'
            ][
                'avax_rate'
            ]

            self.pprint(hass_data)
            r.append(hass_data)
        return r

    def push_to_hass(self, data):
        if self.args.hass:
            for i, v in enumerate(data):
                hu = self.args.hass[i]
                hass.push_to_hass(hu, self.args.hass_token, v)


if __name__ == '__main__':
    CLI()()
