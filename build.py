#!/usr/bin/env -S python3 -u

from builder import cli
from builder.image import AlpineMixin, BaseMixin, Image


class MetaMask(AlpineMixin, Image):
    pass


class Degiro(AlpineMixin, Image):
    pass


class KucoinX(AlpineMixin, Image):
    pass


class Financas(AlpineMixin, Image):
    pass


class CaixaBreak(AlpineMixin, Image):
    pass


class CryptoCom(AlpineMixin, Image):
    pass


class AforroNet(AlpineMixin, Image):
    pass


class IBFetch(AlpineMixin, Image):
    pass


class BaseAlpine(BaseMixin, Image):
    PYTHON_VERSION = 3.13


if __name__ == '__main__':
    cli.cli()
