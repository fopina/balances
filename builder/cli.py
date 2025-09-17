import argparse
from functools import lru_cache
import subprocess
from typing import Dict

from .image import Image

ALL_CHOICE = 'all'


class CLI:
    @lru_cache()
    def discover_images(self) -> Dict[str, any]:
        images = {ALL_CHOICE: Image}
        images.update({c.__name__.lower(): c for c in [*Image.__subclasses__()]})
        return images

    def parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'name',
            nargs='+',
            type=str.lower,
            choices=self.discover_images().keys(),
            help='Name of image (or family of images) you want to build',
        )
        parser.add_argument(
            '-p',
            '--push',
            action='store_true',
            help='Build for all platforms and push image. Default is to do local build only.',
        )
        parser.add_argument('--dry', action='store_true', help='Print docker build commands, do not execute anything.')
        parser.add_argument('--docker-extra', type=str, help='Extra options to be passed to docker build command')
        return parser

    def run(self, argv=None):
        args = self.parser().parse_args(argv)
        images = self.discover_images()
        targets = []

        if ALL_CHOICE in args.name:
            targets = [c for c in images.values() if c != Image]
        else:
            for n in args.name:
                targets.append(images[n])

        for n in targets:
            nc: Image = n(push=args.push, docker_extra=args.docker_extra)
            if args.dry:
                print(nc.build_command())
            else:
                nc.build()
                print(f'Images: {nc.get_full_tags()}')


def cli(argv=None):
    try:
        CLI().run(argv)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)
