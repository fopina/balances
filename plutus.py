import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from selenium.webdriver.common.by import By as By

from common.cli.otp import OTPMixin
from common.cli.selenium import SeleniumCLI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    URL = "https://hasura.plutus.it/v1alpha1/graphql"

    def __init__(self, client_id, refresh_token):
        super().__init__()
        self._client_id = client_id
        self._refresh_token = refresh_token

    def update_auth(self, token):
        self.headers.update(
            {
                "Content-Type": "application/json",
                "User-Agent": "plutus/10 CFNetwork/1333.0.4 Darwin/21.5.0",
                "Accept": "*/*",
                "Accept-Language": "en-GB,en;q=0.9",
                "Authorization": f"Bearer {token}",
            }
        )

    def refresh_token(self):
        data = {
            "client_id": self._client_id,
            "refresh_token": self._refresh_token,
        }
        r = self.post("https://authenticate.plutus.it/auth/refresh-token", json=data).json()
        self.update_auth(r["id_token"])

    def request(self, method, url, *args, **kwargs):
        r = super().request(method, url or self.URL, *args, **kwargs)
        r.raise_for_status()
        return r

    def pluton_balance(self):
        return self.post(
            "",
            json={
                "operationName": None,
                "variables": {},
                "query": "{\n  pluton_balance {\n    available_amount\n    amount\n    created_at\n    __typename\n  }\n}",
            },
        ).json()

    def exchange_rates(self):
        return self.post(
            "",
            json={
                "operationName": "getExchangeRates",
                "variables": {
                    "currencies": ["PLU"],
                    "since": "2022-07-10T08:31:54.780Z",
                    "limit": 1,
                },
                "query": "query getExchangeRates($currencies: [enum_exchange_rates_crypto_currency!], $since: timestamptz!, $limit: Int!) {\n  exchange_rates(\n    where: {crypto_currency: {_in: $currencies}, created_at: {_gt: $since}}\n    limit: $limit\n    order_by: {created_at: desc}\n  ) {\n    rates\n    id\n    crypto_currency\n    created_at\n    __typename\n  }\n}",
            },
        ).json()

    def fiat_balance(self):
        return self.post(
            "",
            json={
                "operationName": "getBalance",
                "variables": {"currency": "EUR"},
                "query": "query getBalance($currency: enum_fiat_balance_currency!) {\n  fiat_balance(where: {currency: {_eq: $currency}}) {\n    id\n    user_id\n    currency\n    amount\n    created_at\n    updated_at\n    __typename\n  }\n}",
            },
        ).json()

    def transaction_list(self):
        r = self.get("https://api.plutus.it/platform/transactions/pluton")
        return r.json()


class CLI(OTPMixin, SeleniumCLI):
    def extend_parser(self, parser):
        parser.add_argument("username")
        parser.add_argument("password")
        parser.add_argument("client_id")
        parser.add_argument(
            "-f",
            "--token-file",
            type=Path,
            default="plutus.local",
            help="File to store the refresh_token",
        )

    def get_client(self, args):
        if args.token_file.exists():
            rtoken = args.token_file.read_text().strip()
            client = Client(args.client_id, rtoken)
            try:
                client.refresh_token()
                return client
            except Exception as e:
                logger.exception("invalid token, logging back in")

        tries = 0
        while True:
            try:
                rtoken = self.login_and_token()
                print(f'PLUTUS: LOGIN SUCCESS ON TRY {tries}')
                break
            except ClientError:
                raise
            except Exception as e:
                tries += 1
                if tries == 3:
                    raise
                print(f'PLUTUS: try {tries}: {e}')
                time.sleep(5)

        with args.token_file.open("w") as f:
            f.write(rtoken)
        client = Client(args.client_id, rtoken)
        client.refresh_token()
        return client

    def login_and_token(self):
        otp=self.otp_holder(self.args),
        logger.info("logging in")
        driver = self.get_webdriver()
        driver.implicitly_wait(20)
        driver.get("https://dex.plutus.it/auth/login/")
        el = driver.find_element("id", "email")
        logger.info("found login form")
        el.send_keys(self.args.username)
        # input-error
        el = driver.find_element("id", "password")
        el.send_keys(self.args.password)
        el.submit()
        if otp:
            el = driver.find_element(By.CSS_SELECTOR, "#code,div.input-error")
            if el.tag_name == 'div':
                raise ClientError(el.get_attribute('innerHTML'))
            logger.info("found OTP form")
            el.send_keys(otp(as_string=True).decode())
            el.submit()
        el = driver.find_element(By.CSS_SELECTOR, "a[href='/dashboard/settings'],div.input-error")
        if el.tag_name == 'div':
            raise ClientError(el.get_attribute('innerHTML'))
        logger.info("logged in!")
        refresh_token = driver.execute_script("return localStorage.refresh_token;")
        driver.quit()
        return refresh_token

    def handle(self, args):
        client = self.get_client(args)

        hass_data = {
            "state": 0,
            "attributes": {
                "unit_of_measurement": "EUR",
            },
        }

        fx = client.exchange_rates()["data"]["exchange_rates"][0]["rates"]["EUR"]
        hass_data["attributes"]["fx"] = fx

        tokens = client.pluton_balance()["data"]["pluton_balance"][0]
        hass_data["attributes"]["avail_amt"] = tokens["available_amount"]
        hass_data["attributes"]["avail_val"] = tokens["available_amount"] * fx
        # WARNING: named "locked_amt" but it is not LOCKED, it's the total wallet!
        # not changing now due to history
        hass_data["attributes"]["locked_amt"] = tokens["amount"]
        hass_data["attributes"]["locked_val"] = tokens["amount"] * fx
        hass_data["state"] += hass_data["attributes"]["locked_val"]

        fiat = client.fiat_balance()["data"]["fiat_balance"][0]["amount"]
        hass_data["attributes"]["fiat_val"] = fiat
        hass_data["state"] += fiat

        amount = 0
        date = None
        for ttx in reversed(client.transaction_list()):
            if not ttx['available']:
                date_str = ttx['createdAt'].split('T')[0]
                if date is not None and date != date_str:
                    break
                amount += float(ttx['amount'])
                date = date_str
        if date is None:
            hass_data["attributes"]["next_vest"] = '-'
            hass_data["attributes"]["next_vest_amt"] = 0
        else:
            hass_data["attributes"]["next_vest"] = datetime.strftime(
                datetime.strptime(date, '%Y-%m-%d') + timedelta(days=46), '%Y-%m-%d'
            )
            hass_data["attributes"]["next_vest_amt"] = amount
        self.pprint(hass_data)
        return hass_data


if __name__ == "__main__":
    CLI()()
