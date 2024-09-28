#!/usr/bin/env -S python3 -u

from typing import Dict, List, Tuple
from builder import cli
from builder.image import Image, ImageMixin
from functools import lru_cache

    
class Node(ImageMixin):
    DOCKERFILE = 'node/Dockerfile'
    CONTEXT = 'node'
    IMAGE = 'base/node'

    def get_tag(self) -> List[str]:
        return self.NODE_MAJOR

    def get_build_args(self) -> Dict[str, str]:
        return {'NODE_MAJOR': self.NODE_MAJOR}


class Node16(Node, Image):
    NODE_MAJOR = '16'


class Node18(Node, Image):
    NODE_MAJOR = '18'


class Node20(Node, Image):
    NODE_MAJOR = '20'


class Python(ImageMixin):
    DOCKERFILE = 'python/Dockerfile'
    CONTEXT = 'python'
    IMAGE = 'base/python'


class Python38(Python, Image):
    BUILD_ARGS = {'PYTHON_PACKAGE': 'python38'}
    TAG = '3.8'


class Python311(Python, Image):
    BUILD_ARGS = {'PYTHON_PACKAGE': 'python311'}
    TAG = '3.11'


class Python312(Python, Image):
    BUILD_ARGS = {'PYTHON_PACKAGE': 'python312'}
    TAG = '3.12'


class Semgrep(ImageMixin):
    DOCKERFILE = 'semgrep/Dockerfile'
    CONTEXT = 'semgrep'
    IMAGE = 'semgrep'

    @lru_cache()
    def _get_semgrep_version(self) -> Tuple[Tuple[int], str]:
        # parse and validate version
        version_string = self.get_parameter('SEMGREP_VERSION')
        try:
            version = list(map(int, version_string.split('.')))
            assert len(version) == 3
            return tuple(version), version_string
        except:
            raise ValueError(f'SEMGREP_VERSION has an invalid value ({version_string}), expected X.Y.Z')

    def get_build_args(self) -> Dict[str, str]:
        return {'SEMGREP_VERSION': self._get_semgrep_version()[1]}
    
    def get_tag(self):
        return self._get_semgrep_version()[1]

    def get_full_tags(self) -> List[str]:
        s = super().get_full_tags()
        if self.get_parameter("SEMGREP_LATEST") == '1':
            s.append(f'{self.IMAGE_BASE}/{self.get_image()}:{self.LATEST_TAG}')
        return s


class SemgrepPython(Semgrep, Image):
    LATEST_TAG = 'latest'

    def get_build_args(self) -> Dict[str, str]:
        args = super().get_build_args()
        if self._get_semgrep_version()[0] >= (1, 84, 0):
            args['BASE_TAG'] = '3.12'
        return args


class SemgrepCore(Semgrep, Image):
    LATEST_TAG = 'core'

    def build_command(self) -> List[str]:
        return super().build_command() + ['--target', 'core']
    
    def get_tag(self):
        return f'{self.LATEST_TAG}-{super().get_tag()}'


if __name__ == '__main__':
    cli.cli()
