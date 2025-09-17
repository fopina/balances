from dataclasses import dataclass
from pathlib import Path
import re
import classyclick
import click
import requests
import json
import logging
import time

from common.cli_ng.selenium import SeleniumCLI
from common.cli_ng.sms_auth import SMSAuthMixin
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class Client(requests.Session):
    URL = 'https://netbenefitsww.fidelity.com/'

    def __init__(self, cookies):
        super().__init__()
        self.cookies.update(cookies)
        self.headers.update(
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
            }
        )
        self._client_id = None

    def request(self, method: str, url: str, *args, **kwargs):
        if not url.startswith('https://'):
            url = f"{self.URL}{url.lstrip('/')}"
        return super().request(method, url, *args, **kwargs)

    def load_plan_data(self):
        r = self.get('/mybenefitsww/spsnav/navigation/PlanSummary')
        if '<title>Log In to Fidelity NetBenefits</title>' in r.text:
            # force a proper status code!
            r.status_code = 403
        r.raise_for_status()
        client_re = re.compile(r'var contextClientId =  "(\d+)";')
        for line in r.text.splitlines():
            m = client_re.findall(line)
            if m:
                self._client_id = m[0]
                break
        else:
            raise click.ClickException('portfolio data not found')

    def get_portofolio_accounts(self):
        r = self.get(
            f'/mybenefitsww/spsplanservices/stockplans/relationships/clients/{self._client_id}/portfolio-accounts'
        )
        r.raise_for_status()
        return r.json()

    def get_plan(self, plan_type: str, plan_ids: list[str], account_number: str, participant_type: str):
        r = self.post(
            f'/mybenefitsww/spsplanservices/stockplans/relationships/clients/{self._client_id}/plans',
            json={
                "planTypeIds": [{"planType": plan_type, "planIds": plan_ids}],
                "exercisablePlanTypeIds": [],
                "userDetails": {
                    "brokerageAccount": {"accountNumber": account_number, "authorizedAccount": False},
                    "filActivated": False,
                    "participantType": participant_type,
                },
            },
        )
        r.raise_for_status()
        return r.json()

    def get_account_balance(self):
        r = self.get('/mybenefitsww/spsaccounts/api/account-balance')
        r.raise_for_status()
        return r.json()


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    username: str = classyclick.Argument()
    password: str = classyclick.Argument()
    screenshot: bool = classyclick.Option(help='Take screenshot on exception')
    token_file: Path = classyclick.Option(
        '-f',
        default=".fidelity.local",
        help="File to store current cookies",
    )
    plan_id: str = classyclick.Option(help='If more than 1 plan, use this to specify the plan ID to track')


@classyclick.command()
class CLI(SMSAuthMixin, SeleniumCLI, Args):
    def handle(self):
        client = self.get_client()
        balance = client.get_account_balance()
        summary = client.get_portofolio_accounts()

        account_number = balance['accountNumber']
        cash_balance = float(balance['assetCurrencyBalance']['coreBalance']['value'])
        share_balance = float(balance['assetCurrencyBalance']['marketValue']['value'])

        if not self.plan_id and len(summary['planSummary']['plans']) > 1:
            raise click.ClickException(
                f'Multiple plans found, use --plan-id to specify which to track: {[plan['planId'] for plan in summary['planSummary']['plans']]}'
            )

        plan_data = None
        for plan in summary['planSummary']['plans']:
            assert plan['planType'] == 'RSU', f'Plan type not supported: {plan}'
            if self.plan_id and self.plan_id != plan['planId']:
                continue
            plan_data = client.get_plan(plan['planType'], [plan['planId']], account_number, summary['participantType'])
            break
        else:
            raise click.ClickException('No plan found, what are you tracking??')

        assert len(plan_data['plans']) == 1, f'{plan["planId"]} has no data?'
        plan_data = plan_data['plans'][0]
        hass_data = {
            'state': float(summary['planSummary']['totalPlanBalance']['amount']),
            'attributes': {
                'unit_of_measurement': 'USD',
                'cash': cash_balance,
                'share_balance': share_balance,
                'shares_vested': int(float(plan_data['totalDistributedAwards'])),
                'shares_unvested': int(float(plan_data['totalUnvestedAwards'])),
                'lastStockPrice': float(summary['stockQuote']['price']),
                'nextDistributionValue': float(plan_data['nextPaymentValue']),
                'nextDistributionUnits': int(float(plan_data['nextPaymentQuantity'])),
                'nextDistributionDate': plan_data['nextPaymentDate'],
            },
        }
        self.pprint(hass_data)
        return hass_data

    def get_client(self):
        if self.token_file.exists():
            cookies = json.loads(self.token_file.read_text())
            client = Client(cookies)
            try:
                client.load_plan_data()
                return client
            except requests.exceptions.HTTPError as e:
                logger.warning('session expired: %s', e)
        _try = 0
        while True:
            try:
                cookies = self.login_and_token()
                print(f'LOGGED IN ON TRY {_try}')
                break
            except WebDriverException as e:
                # Message: unknown error: session deleted because of page crash
                if 'page crash' in str(e):
                    if _try < 3:
                        continue
                raise

        with self.token_file.open("w") as f:
            f.write(json.dumps(cookies))

        client = Client(cookies)
        client.load_plan_data()
        return client

    def login_and_token(self):
        logger.info("logging in")
        driver = self.get_webdriver()
        driver.implicitly_wait(20)
        cookies = {}

        try:
            driver.get("https://nb.fidelity.com/public/nb/worldwide/home")
            logger.info("wait for form...")
            logger.info("found login form")
            el = driver.find_element(By.ID, "dom-username-input")
            el.send_keys(self.username)

            el = driver.find_element(By.ID, "dom-pswd-input")
            el.send_keys(self.password)
            el.send_keys('\n')

            for _ in range(300):
                print('.', end='')
                if 'navigation/PlanSummary' in driver.current_url:
                    break
                if 'pvd-alert__message' in driver.page_source:
                    el = driver.find_element(By.CSS_SELECTOR, 'p.pvd-alert__message')
                    raise click.ClickException(f'Failed login: {el.text.strip()}')
                if '''Sorry, we can't complete this action right now.''' in driver.page_source:
                    # rate limiting on failed logins...?
                    raise click.ClickException('Failed login: CANNOT DO THIS RIGHT NOW???')
                if '''we'll send a temporary code to your phone''' in driver.page_source:
                    self.fail_if_no_sms_auth()
                    el_sms = driver.find_element(By.ID, "dom-channel-list-primary-button")
                    assert el_sms.text == 'Text me the code', 'Text me button does not have the right label'

                    # check cookie wall first
                    el_cookie = driver.find_element(By.ID, "onetrust-accept-btn-handler")
                    el_cookie.click()

                    el_sms.click()

                    sms_code = self.prompt_code()
                    # do not ask again
                    el_otp = driver.find_element(By.ID, "dom-trust-device-checkbox")
                    if not el_otp.is_selected():
                        # why is not clickable by the browser...?
                        driver.execute_script("arguments[0].click();", el_otp)

                    el_otp = driver.find_element(By.ID, "dom-otp-code-input")
                    el_otp.send_keys(sms_code)
                    el_otp.send_keys('\n')
                time.sleep(0.1)
            else:
                raise Exception('timed out logging in...')

            cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
        except Exception:
            if self.screenshot:
                driver.save_screenshot(self.screenshot)
            raise
        finally:
            driver.quit()

        return cookies


if __name__ == '__main__':
    CLI.click()
