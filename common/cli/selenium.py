from . import BasicCLI
from .. import webdriver


class SeleniumCLI(BasicCLI):
    def build_parser(self):
        p = super().build_parser()
        webdriver.selenium_parser(p)
        return p

    def get_webdriver(self, **kwargs):
        if self.args.grid:
            return webdriver.MyRemoteDriver(command_executor=self.args.grid, headless=not self.args.headful, **kwargs)

        return webdriver.MyDriver(
            headless=not self.args.headful, remote_debug_port=self.args.remote_debugging_port, **kwargs
        )
