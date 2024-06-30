from . import BasicCLI
from .. import webdriver


class SeleniumCLI(BasicCLI):
    def build_parser(self):
        p = super().build_parser()
        webdriver.selenium_parser(p)
        return p

    def get_webdriver(self, *args, **kwargs):
        # return webdriver.MyDriver(
        #     *args, docker=self.args.docker, remote_debug_port=self.args.remote_debugging_port, **kwargs
        # )
        return webdriver.MyRemoteDriver()
