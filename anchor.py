import argparse
import json
import urllib.parse
import urllib.request

from common.hass import hass_parser, push_to_hass


def post(url, data, headers=None):
    if headers is None:
        headers = {}
    headers.update({'Content-Type': 'application/json', 'User-Agent': 'curl/7.79.1'})
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def query(query, variables={}):
    r = post('https://mantle.terra.dev/', {'query': query, 'variables': variables})
    if 'errors' in r:
        raise Exception(r['errors'])
    return r['data']


def usd_rate():
    with urllib.request.urlopen(
        'https://api.coingecko.com/api/v3/simple/price?ids=terrausd&vs_currencies=usd'
    ) as response:
        return json.loads(response.read())['terrausd']['usd']


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('market_contract')
    parser.add_argument('your_contract')
    parser.add_argument('your_wallet')
    hass_parser(parser)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    bh = query(
        '''
        query {
            LastSyncedHeight
        }
        '''
    )

    last_block = bh['LastSyncedHeight'] + 1

    query_msg_market = {'epoch_state': {'block_height': last_block}}
    query_msg_balance = {'balance': {'address': args.your_wallet}}

    info = query(
        r'''
        query ($marketContract: String!, $contract: String!, $walletAddress: String!, $queryMsg1: String!, $queryMsg2: String!) {
            moneyMarketEpochState: WasmContractsContractAddressStore(
                ContractAddress: $marketContract
                QueryMsg: $queryMsg1
            ) {
                Result
                Height
            }
            tokenBalance: WasmContractsContractAddressStore(
                ContractAddress: $contract
                QueryMsg: $queryMsg2
            ) {
                Result
                Height
            }
            nativeTokenBalances: BankBalancesAddress(Address: $walletAddress) {
                Result {
                    Denom
                    Amount
                }
            }
        }
        ''',
        variables={
            'marketContract': args.market_contract,
            'contract': args.your_contract,
            'walletAddress': args.your_wallet,
            'queryMsg1': json.dumps(query_msg_market),
            'queryMsg2': json.dumps(query_msg_balance),
        },
    )

    rate = json.loads(info['moneyMarketEpochState']['Result'])['exchange_rate']
    balance = json.loads(info['tokenBalance']['Result'])['balance']
    leftover = info['nativeTokenBalances']['Result'][0]['Amount']
    ust_balance = (float(rate) * int(balance)) / 1000000
    usd_balance = ust_balance * usd_rate()

    if args.hass:
        push_to_hass(
            args.hass[0],
            args.hass[1],
            {
                'state': ust_balance,
                'attributes': {
                    'extra_ust': leftover,
                    'balance': balance,
                    'rate': rate,
                    'usd': usd_balance,
                    'unit_of_measurement': 'UST',
                },
            },
        )


if __name__ == '__main__':
    main()
