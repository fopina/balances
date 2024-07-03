import time
import requests
from pathlib import Path
from common.cli.selenium import SeleniumCLI
from selenium.webdriver.common.by import By as By
import logging
import json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = "https://www.interactivebrokers.co.uk/portal.proxy/v1/portal/"

    def __init__(self, cookies):
        super().__init__()
        self.cookies.update(cookies)
        self.headers.update(
            {
                'User-Agent': SeleniumCLI.DEFAULT_USER_AGENT,
            },
        )

    def request(self, method, url, *args, **kwargs):
        url = url if url.startswith('https://') else f'{self.URL}{url}'
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def validate(self):
        return self.get('sso/validate').json()


class CLI(SeleniumCLI):
    def extend_parser(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument(
            "-f",
            "--token-file",
            type=Path,
            default="ibfetch.local",
            help="File to store current cookies",
        )
        parser.add_argument('--screenshot', action='store_true', help='Take screenshot on exception')

    def get_client(self, args):
        if args.token_file.exists():
            cookies = json.loads(args.token_file.read_text())
            client = Client(cookies)
            try:
                client.validate()
                return client
            except requests.exceptions.HTTPError as e:
                logger.warning('session expired: %s', e)

        tries = 0
        while True:
            try:
                cookies = self.login_and_token()
                print(f'IBFETCH: LOGIN SUCCESS ON TRY {tries}')
                break
            except ClientError:
                raise
            except Exception as e:
                tries += 1
                if tries == 3:
                    raise
                print(f'IBFETCH: try {tries}: {e}')
                time.sleep(5)

        with args.token_file.open("w") as f:
            f.write(json.dumps(cookies))

        client = Client(cookies)
        return client

    def login_and_token(self):
        logger.info("logging in")
        driver = self.get_webdriver()
        driver.implicitly_wait(20)
        cookies = {}
        try:
            driver.get("https://www.interactivebrokers.co.uk/sso/Login")
            el = driver.find_element(By.NAME, "username")
            # accept privacy cookies
            driver.add_cookie({"name": "IB_PRIV_PREFS", "value": "0%7C0%7C0"})
            driver.get("https://www.interactivebrokers.co.uk/sso/Login")
            el = driver.find_element(By.NAME, "username")
            time.sleep(1)
            logger.info("found login form")
            el.send_keys(self.args.username)
            el = driver.find_element(By.NAME, "password")
            el.send_keys(self.args.password)
            el.submit()

            el = driver.find_element(By.CSS_SELECTOR, "a[href='#/portfolio'],div.xyz-errormessage:not(:empty)")
            if el.tag_name == 'div':
                raise ClientError(el.get_attribute('innerHTML'))
            time.sleep(1)
            logger.info("logged in!")
            cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
        except Exception:
            if self.args.screenshot:
                driver.save_screenshot(str(self.args.token_file.parent / 'ibfetch-debug.png'))
            raise
        finally:
            driver.quit()
        return cookies

    def handle(self, args):
        client = self.get_client(args)
        r = client.get('portfolio/accounts').json()
        acc_id = r[0]['accountId']

        hass_data = {
            "state": 0,
            "attributes": {
                "unit_of_measurement": "USD",
            },
        }

        positions = client.get(f'portfolio2/{acc_id}/positions').json()
        for pos in positions:
            ticker = pos['description'].lower()
            val = pos['marketValue']
            hass_data['attributes'][f'{ticker}_size'] = pos['position']
            hass_data['attributes'][f'{ticker}_val'] = val
            hass_data["state"] += val

        ledger = client.get(f'portfolio/{acc_id}/ledger').json()
        for cur, curd in ledger.items():
            ticker = cur.lower()
            val = curd['cashbalance']
            hass_data['attributes'][f'{ticker}_fiat'] = val
            hass_data["state"] += val

        self.pprint(hass_data)
        return hass_data


if __name__ == "__main__":
    CLI()()
