import requests
import json


def parser(parser):
    return hass_parser(parser)


def hass_parser(parser):
    parser.add_argument('--hass', nargs=2, metavar=('ENTITY_URL', 'TOKEN'), help='push to HASS')


def push_to_hass(hass_url, hass_token, hass_data, verify=True):
    r = requests.post(
        hass_url,
        json=hass_data,
        headers={'Authorization': f'Bearer {hass_token}'},
        verify=verify,
    )
    r.raise_for_status()
    print(r.json())


def pprint(data):
    print(json.dumps(data, indent=4))
