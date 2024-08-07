from web3 import Web3
from web3.middleware import geth_poa_middleware

from common.cli import BasicCLI, fx, hass

CONTRACT_RACE = '0x58B699642f2a4b91Dd10800Ef852427B719dB1f0'
CONTRACT_SLIME = '0x5a15Bdcf9a3A8e799fa4381E666466a516F2d9C8'
CONTRACT_SNAILNFT = '0xec675B7C5471c67E9B203c6D1C604df28A89FB7f'
CONTRACT_MEGA_RACE = '0xa65592fC7afa222Ac30a80F273280e6477a274e3'
CONTRACT_WAVAX = '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'
CONTRACT_MULTICALL = '0xca11bde05977b3631167028862be2a173976ca11'

ABI_RACE = [
    {
        "inputs": [],
        "name": "claimableRewards",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        'inputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'name': 'dailyRewardTracker',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'name': 'compRewardTracker',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': '', 'type': 'address'}],
        'name': 'rewardTracker',
        'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
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

ABI_MULTICALL = [
    {
        'inputs': [
            {
                'components': [
                    {'internalType': 'address', 'name': 'target', 'type': 'address'},
                    {'internalType': 'bytes', 'name': 'callData', 'type': 'bytes'},
                ],
                'internalType': 'struct Multicall3.Call[]',
                'name': 'calls',
                'type': 'tuple[]',
            }
        ],
        'name': 'aggregate',
        'outputs': [
            {'internalType': 'uint256', 'name': 'blockNumber', 'type': 'uint256'},
            {'internalType': 'bytes[]', 'name': 'returnData', 'type': 'bytes[]'},
        ],
        'stateMutability': 'payable',
        'type': 'function',
    },
    {
        'inputs': [{'internalType': 'address', 'name': 'addr', 'type': 'address'}],
        'name': 'getEthBalance',
        'outputs': [{'internalType': 'uint256', 'name': 'balance', 'type': 'uint256'}],
        'stateMutability': 'view',
        'type': 'function',
    },
]

DECIMALS = 1000000000000000000


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

    @property
    def race_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_RACE), abi=ABI_RACE)

    @property
    def slime_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_SLIME), abi=ABI_ACCOUNT)

    @property
    def snailnft_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_SNAILNFT), abi=ABI_ACCOUNT)

    @property
    def wavax_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_WAVAX), abi=ABI_ACCOUNT)

    @property
    def mega_race_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_MEGA_RACE), abi=ABI_RACE)

    @property
    def multicall_contract(self):
        return self.web3.eth.contract(address=self.web3.to_checksum_address(CONTRACT_MULTICALL), abi=ABI_MULTICALL)

    def multicall_balances(self, wallets: list[str]):
        calls = []
        # balanceOf: snails, wavax, slime
        contracts = [self.snailnft_contract, self.wavax_contract, self.slime_contract]
        for w in wallets:
            for contract in contracts:
                calls.append(
                    (contract.address, contract.encodeABI('balanceOf', args=(w,))),
                )
            calls.append(
                (self.multicall_contract.address, self.multicall_contract.encodeABI('getEthBalance', args=(w,)))
            )
            calls.append((self.race_contract.address, self.race_contract.encodeABI('dailyRewardTracker', args=(w,))))
            calls.append((self.race_contract.address, self.race_contract.encodeABI('compRewardTracker', args=(w,))))
            calls.append(
                (self.mega_race_contract.address, self.mega_race_contract.encodeABI('rewardTracker', args=(w,)))
            )
        x = self.multicall_contract.functions.aggregate(calls).call()
        w_ind = 0
        results = {}
        for y in range(0, len(x[1]), 7):
            results[wallets[w_ind]] = [
                self.web3.to_int(x[1][y]),
                self.web3.to_int(x[1][y + 1]) / DECIMALS,
                self.web3.to_int(x[1][y + 2]) / DECIMALS,
                self.web3.to_int(x[1][y + 3]) / DECIMALS,
                (self.web3.to_int(x[1][y + 4]) + self.web3.to_int(x[1][y + 5])) / DECIMALS,
                self.web3.to_int(x[1][y + 6]) / DECIMALS,
            ]
            w_ind += 1
        return results


class CLI(fx.CryptoFXMixin, BasicCLI):
    def default_parser(self, parser):
        parser.add_argument(
            '--hass', nargs='+', help='URL(s) to push the data to HASS - ONE FOR EACH WALLET SPECIFIED, SAME ORDER'
        )
        parser.add_argument('--hass-token', help='Token to push to HASS')
        parser.add_argument('--insecure', action='store_true', help='Skip SSL validation')

    def extend_parser(self, parser):
        parser.add_argument('wallet', nargs='+')
        parser.add_argument('--web3', default='https://api.avax.network/ext/bc/C/rpc', help='WEB3 Provider HTTP')

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

        multicall_data = Client('', args.web3).multicall_balances(args.wallet)

        r = []
        for wallet in args.wallet:
            client = Client(wallet, args.web3)

            hass_data = {
                'state': 0,
                'attributes': {
                    'unit_of_measurement': 'USD',
                },
            }

            hass_data['attributes']['avax'] = multicall_data[wallet][3]
            hass_data['attributes']['unclaimed'] = multicall_data[wallet][4]
            hass_data['attributes']['claimed'] = multicall_data[wallet][2]
            hass_data['attributes']['unclaimedw'] = multicall_data[wallet][5]
            hass_data['attributes']['wavax'] = multicall_data[wallet][1]
            hass_data['attributes']['snails'] = multicall_data[wallet][0]
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
                hass.push_to_hass(hu, self.args.hass_token, v, verify=not self.args.insecure)


if __name__ == '__main__':
    CLI()()
