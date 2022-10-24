import time
import requests
from pathlib import Path
from common.webdriver import MyDriver
from common.cli.selenium import SeleniumCLI
from selenium.webdriver.common.by import By as By
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = "https://www.interactivebrokers.co.uk/portal.proxy/v1/portal/"

    def __init__(self, cookies):
        super().__init__()
        self.headers.update(
            {
                'Cookie': cookies,
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0',
            },
        )

    def request(self, method, url, *args, **kwargs):
        url = url if url.startswith('https://') else f'{self.URL}{url}'
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def validate(self):
        return self.get('sso/validate').json()


def login_and_token(args):
    logger.info("logging in")
    driver = MyDriver(docker=args.docker)
    driver.implicitly_wait(20)
    try:
        driver.get("https://www.interactivebrokers.co.uk/sso/Login?RL=1")
        el = driver.find_element(By.ID, "user_name")
        # accept privacy cookies
        driver.add_cookie({"name": "IB_PRIV_PREFS", "value": "0%7C0%7C0"})
        driver.get("https://www.interactivebrokers.co.uk/sso/Login?RL=1")
        el = driver.find_element(By.ID, "user_name")
        time.sleep(1)
        logger.info("found login form")
        el.send_keys(args.username)
        el = driver.find_element(By.ID, "password")
        el.send_keys(args.password)
        el.submit()

        el = driver.find_element(By.CSS_SELECTOR, "a[href='#/portfolio'],div#ERRORMSG[style='']")
        if el.tag_name == 'div':
            raise ClientError(el.get_attribute('innerHTML'))
        time.sleep(1)
        logger.info("logged in!")
        refresh_token = driver.execute_script("return document.cookie;")
    except Exception:
        if args.screenshot:
            driver.save_screenshot(str(args.token_file.parent / 'ibfetch-debug.png'))
        raise
    finally:
        driver.quit()
    return refresh_token


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
            cookies = args.token_file.read_text().strip()
            client = Client(cookies)
            try:
                client.validate()
                return client
            except requests.exceptions.HTTPError as e:
                logger.warning('session expired: %s', e)

        tries = 0
        while True:
            try:
                cookies = login_and_token(args)
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
            f.write(cookies)

        client = Client(cookies)
        return client
    
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
