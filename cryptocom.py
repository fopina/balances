import requests

from common.cli import BasicCLI


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = 'https://app.mona.co/'

    def __init__(self, track_id, token):
        super().__init__()
        self.headers.update(
            {
                'Authorization': f'Bearer {token}',
                'X-User-Track-Id': track_id,
                'Accept-Language': 'en-GB,en;q=0.9',
                'Accept': '*/*',
                'User-Agent': 'Monaco iOS (23548)',
                'Connection': 'keep-alive',
                'os-version': '15.5',
            }
        )

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def allocations(self):
        return self.get('portfolio/profit/api/v1/allocations').json()

    def fiat_overview(self):
        return self.get('api/fiat/account/show').json()

    def supercharger_overview(self):
        return self.get('api/supercharger/account/show').json()

    def earn_overview(self):
        return self.get('api/v2/crypto_earn/account/show').json()


class MissionClient(Client):
    URL = 'https://missions-api.crypto.com/api/'

    def center(self):
        return self.get('center').json()

    def redeem(self):
        return self.post('mission/redeem').json()

    def track_activate(self, track_id):
        return self.post('track/activate', json={'track_id': track_id}).json()

    def mission_checkin(self, mission_id):
        return self.post('mission/checkin', json={'mission_id': mission_id}).json()


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('track_id')
        parser.add_argument('token')
    
    def handle(self, args):
        client = Client(args.track_id, args.token)
        mclient = MissionClient(args.track_id, args.token)
        d = mclient.center()
        vault_diamonds = int(d['data']['diamond_balance']['vault_amount'][0]['amount'])
        redeem_balance = int(d['data']['redeem_balances']['total_amount']['amount'])
        if redeem_balance > 0:
            print('redeem diamonds')
            dd = mclient.redeem()
            if not dd['ok']:
                raise Exception(d)

        for track in d['data']['tracks']:
            if track['track_name'] != 'Daily':
                continue
            if not track['track_active']:
                continue
            print('activate track')
            d = mclient.track_activate(track['track_id'])
            if not d['ok']:
                raise Exception(d)
            for m in track['missions']:
                if m['mission_name_translation_key'] == 'mission_detail__title_check_in':
                    if m['streak_complete']:
                        continue
                    print('mission: checking in')
                    d = mclient.mission_checkin(m['mission_id'])
                    if not d['ok']:
                        raise Exception(d)

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'EUR',
                'diamonds': vault_diamonds,
            },
        }
        print(f"diamonds: {vault_diamonds}")

        tokens = client.allocations()

        for k in tokens['coins']:
            _id = k['id'].lower()
            amt = float(k['amount']['amount'])
            val = float(k['price_native']['amount'])
            print(f"{_id}: {val} ({amt})")
            hass_data['attributes'][f'{_id}_amt'] = amt
            hass_data['attributes'][f'{_id}_val'] = val
            hass_data['state'] += val

        eur = float(client.fiat_overview()['account']['balance']['amount'])
        hass_data['attributes']['fiat_val'] = eur
        hass_data['state'] += eur
        print(f'fiat: {eur}')

        eur = float(client.supercharger_overview()['supercharger_account']['total_balance']['amount'])
        hass_data['attributes']['supercharger_val'] = eur
        print(f'supercharger: {eur}')

        eur = float(client.earn_overview()['crypto_earn_account']['total_balance']['amount'])
        hass_data['attributes']['earn_val'] = eur
        print(f'earn: {eur}')

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
