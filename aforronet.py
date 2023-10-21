import requests
import re

from common.cli import BasicCLI


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = 'https://aforronet.igcp.pt/'

    def __init__(self) -> None:
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
            }
        )

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def login(self, username, password, nif):
        r = self.get('Iimf.AforroNet.UI/services/login/Login.aspx')
        r.raise_for_status()

        data = {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'txtIdentificacao':	username,
            'txtSenha':	password,
            'btLoginAfr.x':	"0",
            'btLoginAfr.y':	"0",
        }

        m = re.findall(r'Indique o <strong>(\d+).*</strong> e <strong>(\d+).*</strong>', r.text)
        if not m:
            raise ClientError('NIF positions not found')
        print('nif', m)
        pos = list(map(lambda x: nif[int(x) - 1], m[0]))
        data['dlPrim_Pos'] = pos[0]
        data['dlSeg_Pos'] = pos[1]
        
        m = re.findall(r'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="(.*?)" />', r.text)
        if not m:
            raise ClientError('__VIEWSTATE not found')
        data['__VIEWSTATE'] = m[0]

        m = re.findall(r'<input type="hidden" name="__VIEWSTATEGENERATOR" id="__VIEWSTATEGENERATOR" value="(.*?)" />', r.text)
        if not m:
            raise ClientError('__VIEWSTATEGENERATOR not found')
        data['__VIEWSTATEGENERATOR'] = m[0]

        m = re.findall(r'<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="(.*?)" />', r.text)
        if not m:
            raise ClientError('__EVENTVALIDATION not found')
        data['__EVENTVALIDATION'] = m[0]

        r = self.post('Iimf.AforroNet.UI/services/login/Login.aspx', data=data)
        r.raise_for_status()
        print(r.text)

        print(data)
        print(pos)

        return pos


    def fiat_overview(self):
        return self.get('api/fiat/account/show').json()

    def supercharger_overview(self):
        return self.get('api/supercharger/account/show').json()

    def earn_overview(self):
        return self.get('api/v2/crypto_earn/account/show').json()


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('track_id')
        parser.add_argument('token')

    def handle(self, args):
        client = Client()
        print(client.login(...))
        return
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

        try:
            tokens = client.allocations()

            for k in tokens['coins']:
                _id = k['id'].lower()
                amt = float(k['amount']['amount'])
                val = float(k['price_native']['amount'])
                print(f"{_id}: {val} ({amt})")
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

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
