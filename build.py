#!/usr/bin/env -S python3 -u

from builder import cli
from builder.image import AlpineMixin, AlpineNGMixin, BaseMixin, ChromiumLiteMixin, Image


class MetaMask(AlpineMixin, Image):
    pass


class Degiro(AlpineNGMixin, Image):
    pass


class KucoinX(AlpineMixin, Image):
    pass


class Financas(AlpineMixin, Image):
    pass


class CaixaBreak(AlpineMixin, Image):
    pass


class CryptoCom(AlpineMixin, Image):
    pass


class AforroNet(AlpineNGMixin, Image):
    pass


class IBFetch(ChromiumLiteMixin, Image):
    pass


class BaseAlpine(BaseMixin, Image):
    pass


class BaseAlpineNG(BaseMixin, Image):
    PYTHON_VERSION = 3.13


if __name__ == '__main__':
    cli.cli()
