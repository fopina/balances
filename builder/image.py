import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List


class ImageMixin:
    """Mixin base class just to tag "families" of images"""


class Image:
    PLATFORMS = 'linux/amd64,linux/arm64'
    CWD = Path(__file__).resolve().parent.parent
    IMAGE_BASE = None

    # these are to be defined in subclasses
    CONTEXT = None
    DOCKERFILE = None
    IMAGE = None
    TAG = None
    BUILD_ARGS = {}

    def __init__(self, push=False, docker_extra=None):
        self._push = push
        self._docker_extra = docker_extra

    def get_full_tags(self) -> List[str]:
        """This can be subclassed to add multiple targets or name them differently"""
        assert self.get_tag() is not None
        assert self.get_image() is not None
        return [f'{self.IMAGE_BASE}/{self.get_image()}:{self.get_tag()}']

    def get_tag(self) -> str:
        """This can be overriden with more complex logic"""
        return self.TAG

    def get_image(self) -> str:
        """This can be overriden with more complex logic"""
        return self.IMAGE

    def get_build_args(self) -> Dict[str, str]:
        """This can be overriden with more complex logic"""
        return self.BUILD_ARGS

    def get_revision(self) -> str:
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=self.CWD).decode().strip()

    def get_parameter(self, name) -> str:
        """
        a way for image builders to get external variables
        for now, only reads from ENV
        """
        return os.getenv(name)

    def build_command(self) -> List[str]:
        assert self.DOCKERFILE is not None
        assert self.CONTEXT is not None

        args = [
            'docker',
            'buildx',
            'build',
            '--build-arg',
            f'VCS_REF={self.get_revision()}',
            '-f',
            self.DOCKERFILE,
            self.CONTEXT,
        ]

        if self._push:
            args.extend(['--platform', self.PLATFORMS, '--push'])
        else:
            args.append('--load')

        for k in self.get_full_tags():
            args.extend(['-t', k])

        for k, v in self.get_build_args().items():
            args.extend(['--build-arg', f'{k}={v}'])

        if self._docker_extra:
            args.extend(shlex.split(self._docker_extra))

        return args

    def build(self) -> int:
        return subprocess.check_call(self.build_command(), cwd=self.CWD)


class AlpineMixin(ImageMixin):
    IMAGE_BASE = 'ghcr.io/fopina'
    IMAGE = 'balances'
    DOCKERFILE = 'docker/Dockerfile'
    CONTEXT = '.'
    PYTHON_VERSION = 3.9
    FLAVOR = 'alpine'

    _service = None

    @property
    def service(self):
        return self._service or self.__class__.__name__.lower()

    def get_tag(self):
        return self.service

    def get_full_tags(self):
        x = super().get_full_tags()
        x.append(f'{x[0]}-{self.get_revision()}')
        return x

    def get_revision(self) -> str:
        return str(
            len(
                subprocess.check_output(['git', 'log', '--oneline', f'{self.service}.py', 'docker'], cwd=self.CWD)
                .decode()
                .splitlines()
            )
        )

    def get_build_args(self):
        return {
            'TARGETBASE': f'{self.IMAGE_BASE}/{self.get_image()}:base-{self.PYTHON_VERSION}-{self.FLAVOR}',
            'ENTRY': self.service,
        }


class GCCMixin(AlpineMixin, ImageMixin):
    FLAVOR = 'gcc'


class ChromiumMixin(AlpineMixin, ImageMixin):
    FLAVOR = 'chromium'


class ChromiumLiteMixin(AlpineMixin, ImageMixin):
    @property
    def service(self):
        assert super().service.endswith('lite')
        return super().service[:-4]

    def get_full_tags(self):
        x = super().get_full_tags()[0]
        return [f'{x}-lite', f'{x}-lite-{self.get_revision()}']


class BaseMixin(AlpineMixin, ImageMixin):
    IMAGE_BASE = 'ghcr.io/fopina'
    IMAGE = 'balances'
    DOCKERFILE = 'docker/Dockerfile.base'
    CONTEXT = '.'
    PYTHON_VERSION = 3.9
    FLAVOR = 'alpine'

    def get_tag(self):
        return f'base-{self.PYTHON_VERSION}-{self.FLAVOR}'

    def get_revision(self) -> str:
        return str(len(subprocess.check_output(['git', 'log', '--oneline', 'docker']).decode().splitlines()))

    def get_build_args(self):
        return {
            'BASE': f'python:{self.PYTHON_VERSION}-alpine',
            'BASESLIM': f'python:{self.PYTHON_VERSION}-slim',
        }

    def build_command(self):
        cmd = super().build_command()
        cmd.extend(['--target', self.FLAVOR])
        return cmd
