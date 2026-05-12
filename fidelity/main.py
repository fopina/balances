import asyncio
import json
import logging
import re
import tempfile
import time
from pathlib import Path

import classyclick
import click
import nodriver as uc
import requests
from balances_selenium import SeleniumCLI
from balances_sms_auth import SMSAuthMixin
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class Client(requests.Session):
    URL = 'https://netbenefitsww.fidelity.com/'

    def __init__(self, cookies):
        super().__init__()
        self.cookies.update(cookies)
        self.headers.update(
            {
                'User-Agent': SeleniumCLI.DEFAULT_USER_AGENT,
            }
        )
        self._client_id = None

    def request(self, method: str, url: str, *args, **kwargs):
        if not url.startswith('https://'):
            url = f'{self.URL}{url.lstrip("/")}'
        kwargs.setdefault('timeout', 60)
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
                'planTypeIds': [{'planType': plan_type, 'planIds': plan_ids}],
                'exercisablePlanTypeIds': [],
                'userDetails': {
                    'brokerageAccount': {'accountNumber': account_number, 'authorizedAccount': False},
                    'filActivated': False,
                    'participantType': participant_type,
                },
            },
        )
        r.raise_for_status()
        return r.json()

    def get_account_balance(self):
        r = self.get('/mybenefitsww/spsaccounts/api/account-balance')
        r.raise_for_status()
        return r.json()


class CLI(SMSAuthMixin, SeleniumCLI):
    username: str = classyclick.Argument()
    password: str = classyclick.Argument()
    screenshot: bool = classyclick.Option(help='Take screenshot on exception')
    token_file: Path = classyclick.Option(
        '-f',
        default='.fidelity.local',
        help='File to store current cookies',
    )
    plan_id: str = classyclick.Option(help='If more than 1 plan, use this to specify the plan ID to track')

    def handle(self):
        client = self.get_client()
        balance = client.get_account_balance()
        summary = client.get_portofolio_accounts()

        account_number = balance['accountNumber']
        cash_balance = float(balance['assetCurrencyBalance']['coreBalance']['value'])
        share_balance = float(balance['assetCurrencyBalance']['marketValue']['value'])

        if not self.plan_id and len(summary['planSummary']['plans']) > 1:
            raise click.ClickException(
                f'Multiple plans found, use --plan-id to specify which to track: {[plan["planId"] for plan in summary["planSummary"]["plans"]]}'
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

        with self.token_file.open('w') as f:
            f.write(json.dumps(cookies))

        client = Client(cookies)
        client.load_plan_data()
        return client

    def login_and_token(self):
        return asyncio.run(self.login_and_token_nodriver())

    def nodriver_chrome_path(self):
        chrome_path = Path(
            '/Users/fopina/.cache/selenium/chrome/mac-arm64/141.0.7390.76/'
            'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
        )
        if chrome_path.exists():
            return chrome_path
        return None

    async def login_and_token_nodriver(self):
        logger.info('logging in')
        cookies = {}
        profile_dir = tempfile.TemporaryDirectory(prefix='fidelity-chrome-profile-')
        browser = None
        browser_args = [
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-search-engine-choice-screen',
            '--lang=en-US,en',
            '--window-size=1366,900',
            f'--user-agent={SeleniumCLI.DEFAULT_USER_AGENT}',
        ]

        try:
            browser = await uc.start(
                user_data_dir=profile_dir.name,
                headless=not self.headful,
                browser_executable_path=self.nodriver_chrome_path(),
                browser_args=browser_args,
                lang='en-US',
            )
            page = await browser.get('https://nb.fidelity.com/public/nb/worldwide/home')
            logger.info('wait for form...')
            username = await page.select('#dom-username-input', timeout=30)
            if username is None:
                raise click.ClickException('Failed login: username form not found')
            logger.info('found login form')
            await page.sleep(5)
            await username.click()
            await username.send_keys(self.username)

            password = await page.select('#dom-pswd-input', timeout=20)
            if password is None:
                raise click.ClickException('Failed login: password form not found')
            await password.click()
            await password.send_keys(self.password)

            await page.sleep(3)
            button = await page.select('#dom-login-button', timeout=20)
            if button is None:
                raise click.ClickException('Failed login: login button not found')
            await button.click()

            for _ in range(300):
                print('.', end='')
                current_url = await page.evaluate('location.href', return_by_value=True)
                content = await page.get_content()
                if 'navigation/PlanSummary' in current_url:
                    break
                if 'pvd-alert__message' in content:
                    alert = await page.select('p.pvd-alert__message', timeout=1)
                    alert_text = alert.text.strip() if alert else 'unknown login error'
                    raise click.ClickException(f'Failed login: {alert_text}')
                if """Sorry, we can't complete this action right now.""" in content:
                    if self.headful:
                        print('Failed login: CANNOT DO THIS RIGHT NOW???')
                        await page.sleep(1000)
                    raise click.ClickException('Failed login: CANNOT DO THIS RIGHT NOW???')
                if """we'll send a temporary code to your phone""" in content:
                    print('NEED SMS AUTH')
                    self.fail_if_no_sms_auth()
                    sms_button = await page.select('#dom-channel-list-primary-button', timeout=20)
                    assert sms_button and sms_button.text == 'Text me the code', (
                        'Text me button does not have the right label'
                    )

                    cookie_button = await page.select('#onetrust-accept-btn-handler', timeout=3)
                    if cookie_button:
                        await cookie_button.click()

                    await sms_button.click()

                    sms_code = self.prompt_code()
                    otp_checkbox = await page.select('#dom-trust-device-checkbox', timeout=20)
                    if otp_checkbox:
                        await otp_checkbox.apply('(elem) => { if (!elem.checked) elem.click(); }')

                    otp_input = await page.select('#dom-otp-code-input', timeout=20)
                    if otp_input is None:
                        raise click.ClickException('Failed login: SMS input not found')
                    await otp_input.send_keys(sms_code)
                    await otp_input.send_keys('\n')
                await page.sleep(0.1)
            else:
                raise Exception('timed out logging in...')

            browser_cookies = await browser.cookies.get_all()
            cookies.update({c.name: c.value for c in browser_cookies})
        except Exception:
            if self.screenshot and browser is not None:
                await page.save_screenshot(self.screenshot)
            raise
        finally:
            if browser is not None:
                browser.stop()
            profile_dir.cleanup()

        return cookies

    def login_and_token_selenium(self):
        logger.info('logging in')
        cookies = {}
        options = webdriver.ChromeOptions()
        options.add_argument('--no-first-run')
        options.add_argument('--no-default-browser-check')
        profile_dir = tempfile.TemporaryDirectory(prefix='fidelity-chrome-profile-')
        options.add_argument(f'--user-data-dir={profile_dir.name}')

        driver = None

        try:
            driver = self.get_webdriver(options=options)
            driver.implicitly_wait(20)
            driver.get('https://nb.fidelity.com/public/nb/worldwide/home')
            logger.info('wait for form...')
            logger.info('found login form')
            time.sleep(5)
            el = driver.find_element(By.ID, 'dom-username-input')
            el.click()
            for char in self.username:
                el.send_keys(char)
                time.sleep(0.08)

            el = driver.find_element(By.ID, 'dom-pswd-input')
            el.click()
            for char in self.password:
                el.send_keys(char)
                time.sleep(0.08)

            time.sleep(0.4)
            time.sleep(3)
            driver.find_element(By.ID, 'dom-login-button').click()

            for _ in range(300):
                print('.', end='')
                if 'navigation/PlanSummary' in driver.current_url:
                    break
                if 'pvd-alert__message' in driver.page_source:
                    el = driver.find_element(By.CSS_SELECTOR, 'p.pvd-alert__message')
                    raise click.ClickException(f'Failed login: {el.text.strip()}')
                if """Sorry, we can't complete this action right now.""" in driver.page_source:
                    # rate limiting on failed logins...?
                    if self.headful:
                        print('Failed login: CANNOT DO THIS RIGHT NOW???')
                        time.sleep(1000)
                    raise click.ClickException('Failed login: CANNOT DO THIS RIGHT NOW???')
                if """we'll send a temporary code to your phone""" in driver.page_source:
                    print('NEED SMS AUTH')
                    self.fail_if_no_sms_auth()
                    el_sms = driver.find_element(By.ID, 'dom-channel-list-primary-button')
                    assert el_sms.text == 'Text me the code', 'Text me button does not have the right label'

                    # check cookie wall first
                    el_cookie = driver.find_element(By.ID, 'onetrust-accept-btn-handler')
                    el_cookie.click()

                    el_sms.click()

                    sms_code = self.prompt_code()
                    # do not ask again
                    el_otp = driver.find_element(By.ID, 'dom-trust-device-checkbox')
                    if not el_otp.is_selected():
                        # why is not clickable by the browser...?
                        driver.execute_script('arguments[0].click();', el_otp)

                    el_otp = driver.find_element(By.ID, 'dom-otp-code-input')
                    el_otp.send_keys(sms_code)
                    el_otp.send_keys('\n')
                time.sleep(0.1)
            else:
                raise Exception('timed out logging in...')

            cookies.update({c['name']: c['value'] for c in driver.get_cookies()})
        except Exception:
            if self.screenshot and driver is not None:
                driver.save_screenshot(self.screenshot)
            raise
        finally:
            if driver is not None:
                driver.quit()
            profile_dir.cleanup()

        return cookies


if __name__ == '__main__':
    CLI.click()
