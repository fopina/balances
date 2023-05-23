import argparse
import requests


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = 'https://app.cgd.pt/'

    def __init__(self):
        super().__init__()
        self.headers.update(
            {
                'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 10; Android SDK built for x86_64 Build/QSR1.210802.001)',
                'X-CGD-APP-Version': '2.21.4',
                'X-CGD-APP-Name': 'APP_PREPAGOS',
                'X-1CGD-APP-LANGUAGE': 'pt-PT',
                'X-CGD-APP-Device': 'as5',
            }
        )
        self._session_id = None
        self._config = None

    def request(self, method, url, *args, **kwargs):
        url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def login(self, user, auth):
        r = self.post(
            'pceApi/rest/v1/system/security/authentications/basic',
            headers={'Authorization': f'Basic {auth}'},
            json={},
            params={'u': user, 'includeAccountsInResponse': 'false'},
        )
        r.raise_for_status()
        return r.json()

    def get_balance(self):
        r = self.get('pceApi/rest/v1/business/cards/ppp/prepaid/cards')
        r.raise_for_status()
        return r.json()


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='contract number - use mitm to get the initial POST request')
    parser.add_argument('auth', help='base64 basic string - use mitm to get the initial POST request')
    parser.add_argument('--hass', nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    client = Client()
    client.login(args.username, args.auth)
    data = client.get_balance()

    assert len(data['cards']) == 1

    hass_data = {
        'state': data['cards'][0]['availableCredit'] / 100,
        'attributes': {
            'unit_of_measurement': 'EUR',
        },
    }

    print(f"Balance: {hass_data['state']}")

    if args.hass:
        print(
            requests.post(
                args.hass[0],
                json=hass_data,
                headers={'Authorization': f'Bearer {args.hass[1]}'},
            )
        )


if __name__ == '__main__':
    main()
