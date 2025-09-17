from dataclasses import dataclass
import json
import time
import classyclick
import click
import requests
from .tgquery import TGQueryMixin


@dataclass
class SMSAuthMixin(TGQueryMixin):
    sms_auth: bool = classyclick.Option(
        help="Perform SMS auth",
    )

    def fail_if_no_sms_auth(self, msg='Failed login: sms-auth'):
        if not self.sms_auth:
            raise click.ClickException(msg)

    def prompt_code(self, app_id, prompt='SMS Code'):
        if self.tg_bot:
            return self.tg_prompt(f'*{app_id}* {prompt}')
        else:
            return input(f'{prompt}: ')
