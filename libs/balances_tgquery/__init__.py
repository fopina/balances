import json
import time
from dataclasses import dataclass
from typing import Optional

import classyclick
import requests

TELEGRAM_API_URL = 'https://api.telegram.org/bot'


class TGError(Exception):
    """exception for telegram related errors"""


@dataclass
class TGQueryMixin:
    """Telegram-backed interaction helpers for otherwise unattended scrapers."""

    tg_bot: str = classyclick.Option(
        nargs=2, metavar='TOKEN CHAT_ID', help='For interactive bits, use Telegram instead of stdin'
    )
    ack_reply: bool = True
    tg_topic_id: Optional[int] = None
    _tg_offset: int = 0

    def tg_send_message(self, text, chat_id: str = None):
        """Send a Markdown Telegram message and fail on Bot API errors.

        The default chat comes from the CLI option so scrapers normally do not
        need to know chat ids. Telegram's JSON ``ok`` flag is checked separately
        from HTTP status because the API can return a successful HTTP response
        for an application-level error.
        """
        if chat_id is None:
            chat_id = self.tg_bot[1]

        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}
        if self.tg_topic_id is not None:
            data['message_thread_id'] = self.tg_topic_id

        response = requests.post(
            f'{TELEGRAM_API_URL}{self.tg_bot[0]}/sendMessage',
            data=data,
        )
        response.raise_for_status()
        response_json = response.json()
        if not response_json['ok']:
            raise TGError(response_json.get('description', 'Unknown error'))
        return response_json

    def tg_poll_updates(self, timeout=30, retries: int = None):
        """Yield Telegram updates using long polling and an advancing offset.

        Long polling lets automation wait for human input without busy-looping.
        ``_tg_offset`` is advanced after yielding each update so a caller can
        finish processing the message before it is acknowledged locally. Network
        and decode errors are retried because Telegram polling is often used from
        transient home-network/container environments.
        """
        _try = 0
        url = f'{TELEGRAM_API_URL}{self.tg_bot[0]}/getUpdates'

        while True:
            _try += 1
            if retries is not None and _try > retries:
                break

            params = {
                'offset': self._tg_offset,
                'timeout': timeout,
            }

            try:
                # Use long polling to wait for new updates
                response = requests.get(url, params=params)
                response.raise_for_status()
                updates = response.json()['result']

                if updates:
                    for update in updates:
                        yield update
                        self._tg_offset = update['update_id'] + 1

            except requests.exceptions.RequestException as e:
                print(f'An error occurred while polling for updates: {e}')
                print('Retrying in 5 seconds...')
                time.sleep(5)
            except json.JSONDecodeError as e:
                print(f'Failed to parse JSON response: {e}')
                print('Retrying in 5 seconds...')
                time.sleep(5)

            time.sleep(1)

    def tg_set_message_reaction(self, message_id: int, chat_id: str = None, emoji='👍'):
        """Add an emoji reaction to a Telegram message."""
        if chat_id is None:
            chat_id = self.tg_bot[1]

        response = requests.post(
            f'{TELEGRAM_API_URL}{self.tg_bot[0]}/setMessageReaction',
            data={
                'chat_id': chat_id,
                'message_id': message_id,
                'reaction': json.dumps([{'type': 'emoji', 'emoji': emoji}]),
            },
        )
        response.raise_for_status()
        response_json = response.json()
        if not response_json['ok']:
            raise TGError(response_json.get('description', 'Unknown error'))
        return response_json

    def tg_prompt(self, text, chat_id: str = None, retries: int = None, timeout=30) -> Optional[str]:
        """Send a prompt and return the text of the matching Telegram reply.

        Only replies to the prompt message are accepted, which avoids consuming
        unrelated chat messages as authentication codes when multiple scrapers or
        manual conversations share the same bot.
        """
        sent = self.tg_send_message(text, chat_id=chat_id)
        for u in self.tg_poll_updates(retries=retries, timeout=timeout):
            if 'message' not in u:
                continue
            if u['message'].get('reply_to_message', {}).get('message_id') == sent['result']['message_id']:
                if self.ack_reply:
                    self.tg_set_message_reaction(u['message']['message_id'], chat_id=u['message']['chat']['id'])
                return u['message']['text']
