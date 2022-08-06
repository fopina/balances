import argparse
from .. import hass


class BasicCLI:
    def extend_parser(self, parser):
        """for subclasses to add custom arguments"""

    def build_parser(self):
        parser = argparse.ArgumentParser()
        self.extend_parser(parser)
        parser.add_argument('--hass', nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')
        return parser

    def handle(self, args):
        """for subclasses to implement CLI main"""

    def execute(self, argv=None):
        args = self.build_parser().parse_args(argv)
        hass.push_to_hass(args, self.handle(args))

    def pprint(self, *args, **kwargs):
        hass.pprint(*args, **kwargs)

    def __call__(self, argv=None):
        return self.execute(argv)
