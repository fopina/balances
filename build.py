#!/usr/bin/env -S python3 -u

from builder import cli
from builder.image import Image, AlpineMixin, GCCMixin, ChromiumMixin, BaseMixin


class MetaMask(AlpineMixin, Image): pass
class Anchor(AlpineMixin, Image): pass
class Celsius(AlpineMixin, Image): pass
class Degiro(AlpineMixin, Image): pass
class KucoinX(AlpineMixin, Image): pass
class Financas(AlpineMixin, Image): pass
class CaixaBreak(AlpineMixin, Image): pass
class Luna20(AlpineMixin, Image): pass
class CryptoCom(AlpineMixin, Image): pass
class AforroNet(AlpineMixin, Image): pass

class SnailTrail(GCCMixin, Image): pass

class Plutus(ChromiumMixin, Image): pass
class IBFetch(ChromiumMixin, Image): pass

class BaseAlpine(BaseMixin, Image): pass


class BaseGCC(BaseMixin, Image):
    FLAVOR = 'gcc'


class BaseChromium(BaseMixin, Image):
    FLAVOR = 'chromium'


if __name__ == '__main__':
    cli.cli()
