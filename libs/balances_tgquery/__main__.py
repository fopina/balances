import argparse
import sys

from balances_tgquery import TGQueryMixin


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog='python -m balances_tgquery',
        description='Send a Telegram prompt and print the reply.',
    )
    parser.add_argument(
        'chat_id',
        help='Telegram chat id',
    )
    parser.add_argument('token', help='Telegram bot token')
    parser.add_argument('message', nargs='+', help='Message text to send')
    parser.add_argument(
        '--timeout',
        type=int,
        default=30,
        help='Telegram long-poll timeout in seconds',
    )
    parser.add_argument(
        '--retries',
        type=int,
        default=None,
        help='Maximum poll attempts while waiting for the chat and reply',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    message = ' '.join(args.message)

    tgquery = TGQueryMixin(tg_bot=(args.token, args.chat_id))
    reply = tgquery.tg_prompt(message, timeout=args.timeout, retries=args.retries)
    if reply is None:
        print('No reply received.', file=sys.stderr)
        return 1

    print(reply)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
