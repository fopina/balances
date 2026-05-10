from pathlib import Path

from selenium import webdriver
from selenium.common import exceptions


class ChromiumHelperMixin:
    """Shared Chromium setup decisions for local and remote Selenium drivers."""

    def hide_selenium(self, options: webdriver.ChromeOptions):
        """Apply common flags that make automation less obvious to websites.

        Several banking/exchange sites treat Selenium-specific Chrome switches
        as suspicious. Keeping all of these mitigations together ensures local
        and grid drivers present the same browser profile.
        """
        # hide selenium! all possible flags found online :shrug:
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features')
        options.add_argument('--disable-blink-features=AutomationControlled')

    def go_headless(self, options: webdriver.ChromeOptions):
        """Configure Chrome for unattended/container-friendly execution.

        The GPU, sandbox, and shared-memory flags trade browser hardening for
        reliability in Docker-style environments where those resources are often
        missing or too small. ``start-maximized`` gives pages a desktop viewport
        even when no visible window exists.
        """
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('start-maximized')

    def set_user_agent(self, user_agent: str):
        """Override the runtime user agent through Chrome DevTools Protocol.

        Setting this after driver startup catches the actual browser session,
        which is especially useful for headless Chrome where the default UA can
        reveal automation even if command-line options were already configured.
        """
        # set UA (such as to mask `headlesschrome`)...
        self.execute_cdp_cmd(
            'Network.setUserAgentOverride',
            {'userAgent': user_agent},
        )

    def init_options_in_driver_kwargs(self, extra_driver_kwargs: dict):
        """Extract or create Chrome options before constructing a driver.

        Selenium constructors want ``options`` as a named argument, while callers
        may pass additional driver kwargs. Popping here avoids sending duplicate
        ``options`` later and asserts early if a caller provides the wrong type.
        """
        options = extra_driver_kwargs.pop('options', webdriver.ChromeOptions())
        assert isinstance(options, webdriver.ChromeOptions)
        return options


class MyRemoteDriver(webdriver.Remote, ChromiumHelperMixin):
    """Remote Selenium driver with the same Chromium defaults as local runs."""

    def __init__(
        self, command_executor='http://127.0.0.1:4444', headless=False, user_agent=None, **extra_driver_kwargs
    ):
        """Start a remote Chromium session with scraper-friendly defaults.

        The grid path mirrors ``MyDriver`` as closely as possible so switching
        between local debugging and Selenium Grid does not change scraper
        behavior beyond where the browser is hosted.
        """
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)
        if headless:
            self.go_headless(options)
        super().__init__(command_executor, options=options, **extra_driver_kwargs)
        if user_agent is not None:
            self.set_user_agent(user_agent)

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Send a CDP command through Selenium Remote.

        ``webdriver.Remote`` does not expose Chrome's helper directly, so the CDP
        endpoint is registered on the command executor before dispatching. This
        keeps user-agent override support available for grid sessions too.
        """
        # copied from ChromiumRemoteConnection
        self.command_executor._commands['executeCdpCommand'] = ('POST', '/session/$sessionId/goog/cdp/execute')
        return self.execute('executeCdpCommand', {'cmd': cmd, 'params': cmd_args})['value']


class MyDriver(webdriver.Chrome, ChromiumHelperMixin):
    """Local Chromium driver used by scrapers when no Selenium Grid is set."""

    def __init__(self, headless=False, remote_debug_port=None, user_agent=None, **extra_driver_kwargs):
        """Start a local Chromium session with optional debugging hooks.

        A locally installed Chromium.app is preferred on macOS development
        machines to avoid depending on whichever Chrome binary Selenium finds.
        The remote debugging port is only added when requested so normal
        automated runs do not expose an unnecessary debugging endpoint.
        """
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)

        if Path('/Applications/Chromium.app/Contents/MacOS/Chromium').exists():
            # for dev environment
            options.binary_location = '/Applications/Chromium.app/Contents/MacOS/Chromium'

        if headless:
            self.go_headless(options)
        if remote_debug_port:
            options.add_argument(f'--remote-debugging-port={remote_debug_port}')
        super().__init__(options=options, **extra_driver_kwargs)
        if user_agent is not None:
            self.set_user_agent(user_agent)


exceptions.WebDriverException.__str__ = lambda x: f'Message: {x.msg}\n'
