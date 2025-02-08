import argparse

from .. import hass


class BasicCLI:
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'

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
            hass.push_to_hass(self.args.hass[0], self.args.hass[1], data, verify=not self.args.insecure)

    def pprint(self, *args, **kwargs):
        hass.pprint(*args, **kwargs)
    
    def unhandled_exception(self, exc):
        raise

    def __call__(self, argv=None):
        try:
            return self.execute(argv)
        except Exception as e:
            self.unhandled_exception(e)
