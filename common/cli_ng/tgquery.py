from dataclasses import dataclass
import json
import time
import classyclick
import requests

TELEGRAM_API_URL = "https://api.telegram.org/bot"


class TGError(Exception):
    """exception for telegram related errors"""


@dataclass
class TGQueryMixin:
    tg_bot: str = classyclick.Option(
        nargs=2, metavar='TOKEN CHAT_ID', help='For interactive bits, use Telegram instead of stdin'
    )
    _tg_offset: int = 0

    def tg_send_message(self, text, chat_id: str = None):
        if chat_id is None:
            chat_id = self.tg_bot[1]

        response = requests.post(
            f"{TELEGRAM_API_URL}{self.tg_bot[0]}/sendMessage",
            data={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        )
        response.raise_for_status()
        response_json = response.json()
        if not response_json["ok"]:
            raise TGError(response_json.get('description', 'Unknown error'))
        return response_json

    def tg_poll_updates(self, timeout=30, retries: int = None):
        _try = 0
        url = f"{TELEGRAM_API_URL}{self.tg_bot[0]}/getUpdates"

        while True:
            _try += 1
            if retries is not None and _try > retries:
                break

            params = {
                "offset": self._tg_offset,
                "timeout": timeout,
            }

            try:
                # Use long polling to wait for new updates
                response = requests.get(url, params=params)
                response.raise_for_status()
                updates = response.json()["result"]

                if updates:
                    for update in updates:
                        yield update
                        self._tg_offset = update["update_id"] + 1

            except requests.exceptions.RequestException as e:
                print(f"An error occurred while polling for updates: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print("Retrying in 5 seconds...")
                time.sleep(5)

            time.sleep(1)

    def tg_prompt(self, text, chat_id: str = None, retries: int = None, timeout=30):
        sent = self.tg_send_message(text, chat_id=chat_id)
        for u in self.tg_poll_updates(retries=retries, timeout=timeout):
            if u['message'].get('reply_to_message', {}).get('message_id') == sent['result']['message_id']:
                return u['message']['text']
