import json
import urllib.parse
import urllib.request

from common.cli import BasicCLI


class Client:
    def __init__(self, partner_token, api_key):
        self._headers = {'x-cel-partner-token': partner_token, 'x-cel-api-key': api_key, 'User-Agent': 'Firefox'}

    def get(self, url):
        req = urllib.request.Request(url, headers=self._headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('partner_token')
        parser.add_argument('api_key')

    def handle(self, args):
        client = Client(args.partner_token, args.api_key)
        all_coins = client.get('https://wallet-api.celsius.network/wallet/balance/')
        hass_data = {
            'state': 0,
            'attributes': {
                'total_tokens': 0,
                'unit_of_measurement': 'USD',
            },
        }
        queue = [k for k, v in all_coins['balance'].items() if v != '0']
        queue_l = len(queue)
        for i, k in enumerate(queue):
            print(f'[{i+1}/{queue_l}] {k}')
            r = client.get(f'https://wallet-api.celsius.network/wallet/{k.replace(" ", "%20")}/balance/')
            vf = float(r['amount'])
            hass_data['attributes']['total_tokens'] += vf
            hass_data['attributes'][k] = vf
            usd = float(r['amount_in_usd'])
            hass_data['attributes'][f'{k}_usd'] = usd
            hass_data['state'] += usd

        return hass_data


if __name__ == '__main__':
    CLI()()
