import requests
import json


def parser(parser):
    return hass_parser(parser)


def hass_parser(parser):
    parser.add_argument('--hass', nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')


def push(args, hass_data):
    return push_to_hass(args, hass_data)


def push_to_hass(args, hass_data):
    if args.hass:
        r = requests.post(
            args.hass[0],
            json=hass_data,
            headers={'Authorization': f'Bearer {args.hass[1]}'},
        )
        r.raise_for_status()
        print(r.json())


def pprint(data):
    print(json.dumps(data, indent=4))
