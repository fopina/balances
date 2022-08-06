from . import BasicCLI
from .. import webdriver


class SeleniumCLI(BasicCLI):
    def build_parser(self):
        p = super().build_parser()
        webdriver.selenium_parser(p)
        return p
