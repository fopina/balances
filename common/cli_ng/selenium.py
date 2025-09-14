from .. import webdriver
from . import BasicCLI


class SeleniumCLI(BasicCLI):
    def build_parser(self):
        p = super().build_parser()
        webdriver.selenium_parser(p)
        return p

    def get_webdriver(self, user_agent=BasicCLI.DEFAULT_USER_AGENT, **kwargs):
        kwargs['user_agent'] = user_agent
        if 'headless' not in kwargs:
            kwargs['headless'] = not self.args.headful

        if self.args.grid:
            return webdriver.MyRemoteDriver(command_executor=self.args.grid, **kwargs)

        return webdriver.MyDriver(remote_debug_port=self.args.remote_debugging_port, **kwargs)
