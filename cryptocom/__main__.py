import classyclick
import click
import requests
from balances_cli import BasicCLI


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
        url = f'{self.URL}{url.lstrip("/")}'
        kwargs.setdefault('timeout', 60)
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def allocations(self):
        return self.get('portfolio/profit/api/v1/allocations').json()

    def fiat_overview(self):
        return self.get('api/fiat/account/show').json()

    def supercharger_overview(self):
        return self.get('api/supercharger/account/show').json()

    def earn_overview(self):
        return self.get('api/v2/crypto_earn/account/show').json()

    def daily_reward(self):
        return self.get('api/v1/airdrop-arena/daily-reward').json()


class MissionClient(Client):
    """Legacy missions API, no longer used in the app but still available."""

    URL = 'https://missions-api.crypto.com/api/'

    def center(self):
        return self.get('center').json()

    def redeem(self):
        return self.post('mission/redeem').json()

    def track_activate(self, track_id):
        return self.post('track/activate', json={'track_id': track_id}).json()

    def mission_checkin(self, mission_id):
        return self.post('mission/checkin', json={'mission_id': mission_id}).json()


class RewardsHubClient(Client):
    """Native Rewards Hub API discovered in the Crypto.com app."""

    URL = 'https://missions-api.crypto.com/'

    def missions(self):
        return self.get('api/v1/missions').json()

    def checkin_detail(self):
        return self.get('api/v1/mission/check-in/detail').json()

    def claim_checkin(self, mission_id):
        """Claim check-in using the mission ID from the detail response."""
        return self.post('api/v1/mission/check-in/claim', json={'mission_id': mission_id}).json()

    def claim_mission(self, payload):
        """Claim another mission using the request body captured from the app."""
        return self.post('api/v1/mission/claim', json=payload).json()


class RipsClient(Client):
    URL = 'https://main-app-us-bff.mona.co/api/proxy/rips/'

    def __init__(self, track_id, token, device_id=None):
        super().__init__(track_id, token)
        if device_id:
            self.headers['X-App-Device-Id'] = device_id

    def claimable_packs(self):
        return self.get('api/v1/packs/claimable').json()

    def claim_pack(self, payload):
        """Claim packs using the request body captured from the app."""
        return self.post('api/v1/packs/claim', json=payload).json()


class CLI(BasicCLI):
    track_id: str = classyclick.Argument()
    token: str = classyclick.Argument()
    skip_mission: bool = classyclick.Option(help='Skip diamond collections, just scrape balance')

    def handle(self):
        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'EUR',
                'claims': 0,
            },
        }

        client = Client(self.track_id, self.token)
        try:
            tokens = client.allocations()
            if not tokens['ok'] and tokens['error'] == 'unauthorized':
                raise click.ClickException('Login expired')

            for k in tokens['coins']:
                _id = k['id'].lower()
                amt = float(k['amount']['amount'])
                val = float(k['price_native']['amount'])
                print(f'{_id}: {val} ({amt})')
                hass_data['attributes'][f'{_id}_amt'] = amt
                hass_data['attributes'][f'{_id}_val'] = val
                hass_data['state'] += val
        except requests.exceptions.HTTPError:
            # FIXME: ignoring this for now but need replacement endpoint!
            print('FAILED TO GET ALLOCATIONS #FIXME')

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

        if not self.skip_mission:
            mclient = MissionClient(self.track_id, self.token)
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
                for mission in track['missions']:
                    if mission['mission_name_translation_key'] != ('mission_detail__title_check_in'):
                        continue
                    if mission['streak_complete']:
                        continue
                    print('mission: checking in')
                    d = mclient.mission_checkin(mission['mission_id'])
                    if not d['ok']:
                        raise Exception(d)
                    hass_data['attributes']['claims'] += 1

            hass_data['attributes']['diamonds'] = vault_diamonds
            print(f'diamonds: {vault_diamonds}')

        rewards = RewardsHubClient(self.track_id, self.token)
        rips = RipsClient(self.track_id, self.token)
        checkin = rewards.checkin_detail()

        checkin_data = checkin.get('data', checkin)
        if not self.skip_mission and checkin_data.get('is_claimed') is False:
            mission_id = checkin_data['mission_id']
            print('check-in is unclaimed, claiming it...')
            claim_result = rewards.claim_checkin(mission_id)
            reward_amount = claim_result['reward_amount']
            hass_data['attributes']['claims'] += 1
            print(f'check-in claim: {reward_amount["amount"]} {reward_amount["currency"]}')

        claimable_packs = rips.claimable_packs()
        print(f'rips has_more: {claimable_packs["has_more"]}')
        hass_data['attributes']['rips_has_more'] = claimable_packs['has_more']

        daily_reward = client.daily_reward()
        print(f'airdrop arena points: {daily_reward["points"]}')
        hass_data['attributes']['airdrop_arena_points'] = float(daily_reward['points'])

        print(f'\nTotal: {hass_data["state"]}')
        return hass_data


if __name__ == '__main__':
    CLI.click()
