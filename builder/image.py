import subprocess
import os
import shlex
from typing import Dict, List

class ImageMixin:
    """Mixin base class just to tag "families" of images"""


class Image:
    PLATFORMS = 'linux/amd64,linux/arm64'
    IMAGE_BASE = 'xxx'

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
        # decode() instead of text=True as python 3.6 is still used
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()

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
            'docker', 'buildx', 'build',
            '--build-arg', f'VCS_REF={self.get_revision()}',
            '--build-arg', f'http_proxy={os.getenv("http_proxy")}',
            '--build-arg', f'https_proxy={os.getenv("http_proxy")}',
            '--build-arg', f'HTTP_PROXY={os.getenv("http_proxy")}',
            '--build-arg', f'HTTPS_PROXY={os.getenv("http_proxy")}',
            '--build-arg', f'no_proxy={os.getenv("no_proxy")}',
            '-f', self.DOCKERFILE,
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
        return subprocess.check_call(self.build_command())
