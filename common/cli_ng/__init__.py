import argparse
from dataclasses import dataclass
import sys
import classyclick

from .. import hass


@dataclass
class BasicCLI:
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'
    insecure: bool = classyclick.Option(help='Skip SSL validation')
    hass: str = classyclick.Option(nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')

    def handle(self):
        raise NotImplementedError('subclass must implement this')

    def push_to_hass(self, data):
        if self.hass:
            hass.push_to_hass(self.hass[0], self.hass[1], data, verify=not self.insecure)

    def pprint(self, *args, **kwargs):
        hass.pprint(*args, **kwargs)

    def unhandled_exception(self, exc):
        raise

    def __call__(self):
        try:
            sys.exit(self.push_to_hass(self.handle()) or 0)
        except Exception as e:
            # if unhandled_exception is not specific (None), assume 2
            r = self.unhandled_exception(e)
            if r is None:
                r = 2
            sys.exit(r)
