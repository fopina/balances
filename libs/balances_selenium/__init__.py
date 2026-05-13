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
        automation, but callers can still pass an explicit ``headless`` value for
        one-off debugging. The default user agent masks Selenium's headless
        signature unless a scraper has a site-specific reason to override it.
        """
        import undetected_chromedriver as uc

        driver = uc.Chrome(
            headless=not self.headful,
            use_subprocess=False,
            browser_executable_path='/Users/fopina/.cache/selenium/chrome/mac-arm64/148.0.7778.167/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
        )
        return driver
        kwargs['user_agent'] = user_agent
        if 'headless' not in kwargs:
            kwargs['headless'] = not self.headful

        if self.grid:
            return webdriver.MyRemoteDriver(command_executor=self.grid, **kwargs)

        return webdriver.MyDriver(remote_debug_port=self.remote_debugging_port, **kwargs)
