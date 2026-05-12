import classyclick
from balances_cli import BasicCLI

from . import webdriver


class SeleniumCLI(BasicCLI):
    """CLI mixin for scrapers that need a Chromium WebDriver."""

    headful: bool = classyclick.Option(help='Run Chromium WITHOUT headless mode')
    grid: str = classyclick.Option(help='Use remote chromium (in a selenium grid)')
    remote_debugging_port: int = classyclick.Option(help='chromium remote debugging port')

    def get_webdriver(self, user_agent=BasicCLI.DEFAULT_USER_AGENT, **kwargs):
        """Create the appropriate local or remote Chromium driver.

        Headless mode is the default because these scrapers normally run in
        automation, but callers can still pass an explicit ``headless`` value
        for one-off debugging. The default user agent masks Chrome-for-Testing's
        headless signature unless a scraper has a site-specific reason to use
        the browser's raw UA.
        """
        kwargs['user_agent'] = user_agent
        if 'headless' not in kwargs:
            kwargs['headless'] = not self.headful

        if self.grid:
            return webdriver.MyRemoteDriver(command_executor=self.grid, **kwargs)

        return webdriver.MyDriver(remote_debug_port=self.remote_debugging_port, **kwargs)
