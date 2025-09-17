#!/usr/bin/env python

import argparse
import subprocess
import json
from pathlib import Path

PARAM_MAP = json.loads((Path(__file__).parent / 'test_run.json').read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'script',
        help='Script file to execute',
    )
    parser.add_argument('--docker', '-d', action='store_true', help='Use docker image')
    parser.add_argument('--selenium', '-s', type=str, help='Selenium container name (to use with --link)')
    parser.add_argument("flags", nargs=argparse.REMAINDER, help="Extra arguments to forward to script")

    args = parser.parse_args()

    if args.script.endswith('.py'):
        args.script = args.script[:-3]

    assert args.script in PARAM_MAP, 'not configured'

    secret_key = PARAM_MAP[args.script][0]

    if secret_key:
        secrets = json.loads(subprocess.check_output(['rbw', 'get', '--raw', secret_key]))

    s_args = []
    for s_arg in PARAM_MAP[args.script][1]:
        if s_arg[:2] == 's:':
            s_arg = s_arg[2:]
            if s_arg in ('username', 'password'):
                s_args.append(secrets['data'][s_arg])
            else:
                for f in secrets['fields']:
                    if f['name'] == s_arg:
                        s_args.append(f['value'])
                        break
                else:
                    assert False, f'{s_arg} field not found'
        else:
            s_args.append(s_arg)

    if args.flags:
        s_args.extend(args.flags)

    try:
        if args.docker:
            if args.selenium:
                sel = ['--link', args.selenium]
            else:
                sel = []
            subprocess.check_call(['docker', 'run', '-i'] + sel + [gen_image(args.script)] + s_args)
        else:
            subprocess.check_call(['python', f'{args.script}.py'] + s_args)
    except subprocess.CalledProcessError as e:
        exit(e.returncode)


def gen_image(script):
    return f'ghcr.io/fopina/balances:{script}'


if __name__ == '__main__':
    main()
