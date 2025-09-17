from dataclasses import dataclass

import classyclick

from .. import webdriver
from . import BasicCLI


@dataclass
class SeleniumCLI(BasicCLI):
    headful: bool = classyclick.Option(help="Run Chromium WITHOUT headless mode")
    grid: str = classyclick.Option(help="Use remote chromium (in a selenium grid)")
    remote_debugging_port: int = classyclick.Option(help="chromium remote debugging port")

    def get_webdriver(self, user_agent=BasicCLI.DEFAULT_USER_AGENT, **kwargs):
        kwargs['user_agent'] = user_agent
        if 'headless' not in kwargs:
            kwargs['headless'] = not self.headful

        if self.grid:
            return webdriver.MyRemoteDriver(command_executor=self.grid, **kwargs)

        return webdriver.MyDriver(remote_debug_port=self.remote_debugging_port, **kwargs)
