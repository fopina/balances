"""
Scraper for IBKR.

If using a secondary (read-only) user, make sure it has "Market data" access (under Trading permissions) and "TWS" under Trading platforms.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import classyclick
import click
import requests
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By as By

from common.cli_ng.selenium import SeleniumCLI

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class Client(requests.Session):
    URL = 'https://www.interactivebrokers.ie/portal.proxy/v1/portal/'

    def __init__(self, cookies):
        super().__init__()
        self.cookies.update(cookies)
        self.headers.update(
            {
                'User-Agent': SeleniumCLI.DEFAULT_USER_AGENT,
            },
        )

    def request(self, method: str, url: str, *args, **kwargs):
        url = url if url.startswith('https://') else f'{self.URL}{url}'
        r = super().request(method, url, *args, **kwargs)
        r.raise_for_status()
        return r

    def validate(self):
        return self.get('sso/validate').json()


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    username: str = classyclick.Argument()
    password: str = classyclick.Argument()
    token_file: Path = classyclick.Option(
        '-f',
        default='.ibkr.local',
        help='File to store current cookies',
    )
    screenshot: bool = classyclick.Option(help='Take screenshot on exception')


@classyclick.command()
class CLI(SeleniumCLI, Args):
    def get_client(self):
        if self.token_file.exists():
            cookies = json.loads(self.token_file.read_text())
            client = Client(cookies)
            client.verify = False
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
            except WebDriverException as e:
                tries += 1
                if tries == 3:
                    raise
                print(f'IBFETCH: try {tries}: {e}')
                time.sleep(5)

        with self.token_file.open('w') as f:
            f.write(json.dumps(cookies))

        client = Client(cookies)
        return client

    def login_and_token(self):
        logger.info('logging in')
        driver = self.get_webdriver()
        driver.implicitly_wait(20)
        cookies = {}
        try:
            driver.get('https://www.interactivebrokers.ie/sso/Login')
            el = driver.find_element(By.NAME, 'username')
            # accept privacy cookies
            driver.add_cookie({'name': 'IB_PRIV_PREFS', 'value': '0%7C0%7C0'})
            driver.get('https://www.interactivebrokers.ie/sso/Login')
            el = driver.find_element(By.NAME, 'username')
            time.sleep(1)
            logger.info('found login form')
            el.send_keys(self.username)
            el = driver.find_element(By.NAME, 'password')
            el.send_keys(self.password)
            el.submit()

            el = driver.find_element(
                By.CSS_SELECTOR, "a[href='#/dashboard/positions'],div.xyz-errormessage:not(:empty)"
            )
            if el.tag_name == 'div':
                raise click.ClickException(el.get_attribute('innerHTML'))
            time.sleep(1)
            logger.info('logged in!')
            cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
        except click.ClickException:
            raise
        except Exception:
            if self.screenshot:
                driver.save_screenshot('ibfetch-debug.png')
            print(f'== SOURCE ==\n{driver.page_source}\n== SOURCE END ==')
            raise
        finally:
            driver.quit()
        return cookies

    def handle(self):
        client = self.get_client()
        r = client.get('portfolio/accounts').json()
        acc_id = r[0]['accountId']

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            },
        }

        positions = client.get(f'portfolio2/{acc_id}/positions').json()
        for pos in positions:
            ticker = pos['description'].lower()
            val = pos['marketValue']
            hass_data['attributes'][f'{ticker}_size'] = pos['position']
            hass_data['attributes'][f'{ticker}_val'] = val
            hass_data['state'] += val

        ledger = client.get(f'portfolio/{acc_id}/ledger').json()
        for cur, curd in ledger.items():
            ticker = cur.lower()
            val = curd['cashbalance']
            hass_data['attributes'][f'{ticker}_fiat'] = val
            hass_data['state'] += val

        self.pprint(hass_data)
        return hass_data


if __name__ == '__main__':
    CLI.click()
