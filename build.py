#!/usr/bin/env -S python3 -u

from builder import cli
from builder.image import AlpineNGMixin, BaseMixin, Image


class MetaMask(AlpineNGMixin, Image):
    pass


class Degiro(AlpineNGMixin, Image):
    pass


class KucoinX(AlpineNGMixin, Image):
    pass


class Financas(AlpineNGMixin, Image):
    pass


class CaixaBreak(AlpineNGMixin, Image):
    pass


class CryptoCom(AlpineNGMixin, Image):
    pass


class AforroNet(AlpineNGMixin, Image):
    pass


class IBFetch(AlpineNGMixin, Image):
    pass


class BaseAlpine(BaseMixin, Image):
    PYTHON_VERSION = 3.13


if __name__ == '__main__':
    cli.cli()
