from dataclasses import dataclass

import classyclick
import click
from balances_tgquery import TGQueryMixin


@dataclass
class SMSAuthMixin(TGQueryMixin):
    """Shared SMS-code prompting for scrapers with optional Telegram input."""

    sms_auth: bool = classyclick.Option(
        help='Perform SMS auth',
    )

    def fail_if_no_sms_auth(self, msg='Failed login: sms-auth'):
        """Stop before an SMS flow unless an interactive channel is enabled.

        Telegram counts as authorization because it can supply the code without
        blocking stdin. Without either path, failing early gives automation a
        clear error instead of waiting forever at a prompt.
        """
        if not self.sms_auth and not self.tg_bot:
            raise click.ClickException(msg)

    def prompt_code(self, app_id=None, prompt='SMS Code'):
        """Prompt for an SMS code through Telegram or stdin.

        The scraper name is embedded in Telegram prompts so a shared chat can
        distinguish simultaneous login attempts. Telegram replies are stripped to
        match stdin behavior and to avoid whitespace breaking form submissions.
        """
        if app_id is None:
            app_id = self.scraper_name
        if self.tg_bot:
            code = self.tg_prompt(f'*{app_id}* {prompt}')
            if code is None:
                raise click.ClickException('Failed to get SMS code from Telegram')
            return code.strip()
        else:
            return input(f'{prompt}: ').strip()
