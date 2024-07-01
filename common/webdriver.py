from typing import List
from selenium import webdriver
from pathlib import Path

from selenium.webdriver.common.options import BaseOptions

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'


class ChromiumHelperMixin:
    def hide_selenium(self, options: webdriver.ChromeOptions):
        # hide selenium! all possible flags found online :shrug:
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
    
    def go_headless(self, options: webdriver.ChromeOptions):
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("start-maximized")

    def set_user_agent(self, user_agent: str):
        # set UA (such as to mask `headlesschrome`)...
        self.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": user_agent},
        )
    
    def init_options_in_driver_kwargs(self, extra_driver_kwargs: dict):
        options = extra_driver_kwargs.pop('options', webdriver.ChromeOptions())
        assert isinstance(options, webdriver.ChromeOptions)
        return options


class MyRemoteDriver(webdriver.Remote, ChromiumHelperMixin):
    def __init__(self, command_executor='http://127.0.0.1:4444', headless=False, user_agent=DEFAULT_USER_AGENT, **extra_driver_kwargs):
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)
        if headless:
            self.go_headless(options)
        super().__init__(command_executor, options=options, **extra_driver_kwargs)
        if user_agent is not None:
            self.set_user_agent(user_agent)

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        # copied from ChromiumRemoteConnection
        self.command_executor._commands['executeCdpCommand'] = ('POST', f'/session/$sessionId/goog/cdp/execute')
        return self.execute("executeCdpCommand", {'cmd': cmd, 'params': cmd_args})['value']


class MyDriver(webdriver.Chrome, ChromiumHelperMixin):
    def __init__(
        self, headless=False, remote_debug_port=None, user_agent=DEFAULT_USER_AGENT, **extra_driver_kwargs
    ):
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)

        if Path("/Applications/Chromium.app/Contents/MacOS/Chromium").exists():
            # for dev environment
            options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"

        if headless:
            self.go_headless(options)
        if remote_debug_port:
            options.add_argument(f"--remote-debugging-port={remote_debug_port}")
        super().__init__(options=options, **extra_driver_kwargs)
        if user_agent is not None:
            self.set_user_agent(user_agent)


def selenium_parser(parser):
    parser.add_argument("--headful", action="store_true", help="Run Chromium WITHOUT headless mode")
    parser.add_argument("--grid", type=str, help="Use remote chromium (in a selenium grid)")
    parser.add_argument("--remote-debugging-port", type=int, help="chromium remote debugging port")
