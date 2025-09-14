#!/usr/bin/env -S python3 -u

from builder import cli
from builder.image import AlpineMixin, AlpineNGMixin, BaseMixin, ChromiumLiteMixin, GCCMixin, Image


class MetaMask(AlpineMixin, Image):
    pass


class Anchor(AlpineMixin, Image):
    pass


class Celsius(AlpineMixin, Image):
    pass


class Degiro(AlpineMixin, Image):
    pass


class KucoinX(AlpineMixin, Image):
    pass


class Financas(AlpineMixin, Image):
    pass


class CaixaBreak(AlpineMixin, Image):
    pass


class Luna20(AlpineMixin, Image):
    pass


class CryptoCom(AlpineMixin, Image):
    pass


class AforroNet(AlpineNGMixin, Image):
    pass


class SnailTrail(GCCMixin, Image):
    pass


class Plutus(ChromiumLiteMixin, Image):
    pass


class IBFetch(ChromiumLiteMixin, Image):
    pass


class BaseAlpine(BaseMixin, Image):
    pass


class BaseAlpineNG(BaseMixin, Image):
    PYTHON_VERSION = 3.13


class BaseGCC(BaseMixin, Image):
    FLAVOR = 'gcc'


if __name__ == '__main__':
    cli.cli()
