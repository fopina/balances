from dataclasses import dataclass
import classyclick
import click
from .tgquery import TGQueryMixin


@dataclass
class SMSAuthMixin(TGQueryMixin):
    sms_auth: bool = classyclick.Option(
        help="Perform SMS auth",
    )

    def fail_if_no_sms_auth(self, msg='Failed login: sms-auth'):
        if not self.sms_auth and not self.tg_bot:
            raise click.ClickException(msg)

    def prompt_code(self, app_id=None, prompt='SMS Code'):
        if app_id is None:
            app_id = self.scraper_name
        if self.tg_bot:
            code = self.tg_prompt(f'*{app_id}* {prompt}')
            if code is None:
                raise click.ClickException('Failed to get SMS code from Telegram')
            return code.strip()
        else:
            return input(f'{prompt}: ').strip()
