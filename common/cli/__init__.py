import argparse
from .. import hass


class BasicCLI:
    args: argparse.Namespace

    def extend_parser(self, parser):
        """for subclasses to add custom arguments"""

    def build_parser(self):
        parser = argparse.ArgumentParser()
        self.extend_parser(parser)
        self.default_parser(parser)
        return parser

    def default_parser(self, parser):
        parser.add_argument('--insecure', action='store_true', help='Skip SSL validation')
        parser.add_argument('--hass', nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')

    def handle(self, args):
        """for subclasses to implement CLI main"""

    def execute(self, argv=None):
        self.args = self.build_parser().parse_args(argv)
        # FIXME: remove `args` arg from self.handle (after updating all collectors)
        self.push_to_hass(self.handle(self.args))

    def push_to_hass(self, data):
        if self.args.hass:
            hass.push_to_hass(self.args.hass[0], self.args.hass[1], data)

    def pprint(self, *args, **kwargs):
        hass.pprint(*args, **kwargs)

    def __call__(self, argv=None):
        return self.execute(argv)
