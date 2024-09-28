import argparse
from functools import lru_cache
from typing import Dict
from .image import Image, ImageMixin
import os


class CLI:
    @lru_cache()
    def discover_images(self) -> Dict[str, any]:
        images = {'all':  Image}
        images.update({
            c.__name__.lower(): c
            for c in [*ImageMixin.__subclasses__(), *Image.__subclasses__()]
        })
        return images

    def parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'name', nargs='+', type=str.lower, choices=self.discover_images().keys(), help='Name of image (or family of images) you want to build')
        parser.add_argument('-p', '--push', action='store_true', help='Build for all platforms and push image. Default is to do local build only.')
        parser.add_argument('--dry', action='store_true', help='Print docker build commands, do not execute anything.')
        parser.add_argument('--docker-extra', type=str, help='Extra options to be passed to docker build command')
        return parser

    def run(self, argv=None):
        args = self.parser().parse_args(argv)
        images = self.discover_images()
        targets = []

        if 'all' in args.name:
            targets = [c for c in images.values() if issubclass(c, Image) and c != Image]
        else:
            for n in args.name:
                nc = images[n]
                if issubclass(nc, ImageMixin) and not issubclass(nc, Image):
                    for c in nc.__subclasses__():
                        targets.append(c)
                else:
                    targets.append(nc)

        for n in targets:
            nc: Image = n(push=args.push, docker_extra=args.docker_extra)
            if args.dry:
                print(nc.build_command())
            else:
                nc.build()


def cli(argv=None):
    CLI().run(argv)
