from selenium import webdriver
from pathlib import Path

DEFAULT = object()


class MyDriver(webdriver.Chrome):
    def __init__(self, executable_path="chromedriver", docker=False, remote_debug_port=None, user_agent=DEFAULT, **kwargs):
        options = webdriver.ChromeOptions()
        if Path("/Applications/Chromium.app/Contents/MacOS/Chromium").exists():
            # for dev environment
            options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
        # hide selenium! all possible flags found online :shrug:
        if docker:
            options.headless = True
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("start-maximized")
        if remote_debug_port:
            options.add_argument(f"--remote-debugging-port={remote_debug_port}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        super().__init__(executable_path=executable_path, options=options, **kwargs)
        if user_agent == DEFAULT:
            # set UA by default so that `headlesschrome` is not sent...
            self.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"},
            )
        elif user_agent is not None:
            self.execute_cdp_cmd(
                "Network.setUserAgentOverride",
                {"userAgent": user_agent},
            )


def selenium_parser(parser):
    parser.add_argument("--docker", action="store_true", help="docker mode")
    parser.add_argument("--remote-debugging-port", type=int, help="chromium remote debugging port")
