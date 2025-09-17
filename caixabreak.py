from dataclasses import dataclass

import classyclick
import requests

from common.cli_ng import BasicCLI


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


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    username: str = classyclick.Argument()
    auth: str = classyclick.Argument(metavar='BASE64_BASIC_STRING')


@classyclick.command()
class CLI(BasicCLI, Args):
    def handle(self):
        client = Client()
        client.login(self.username, self.auth)
        data = client.get_balance()

        assert len(data['cards']) == 1

        hass_data = {
            'state': data['cards'][0]['availableCredit'] / 100,
            'attributes': {
                'unit_of_measurement': 'EUR',
            },
        }

        print(f"Balance: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI.click()
