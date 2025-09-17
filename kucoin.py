from dataclasses import dataclass

import classyclick
from kucoin_universal_sdk.api import DefaultClient
from kucoin_universal_sdk.generate.account.account import GetSpotAccountListReq
from kucoin_universal_sdk.generate.account.subaccount import GetSpotSubAccountListV2Req
from kucoin_universal_sdk.generate.spot.market import GetFiatPriceReq
from kucoin_universal_sdk.model import (
    GLOBAL_API_ENDPOINT,
    GLOBAL_BROKER_API_ENDPOINT,
    GLOBAL_FUTURES_API_ENDPOINT,
    ClientOptionBuilder,
    TransportOptionBuilder,
)

from common.cli_ng import BasicCLI


@dataclass
class Args:
    # FIXME: this should be directly in CLI but classyclick does not allow ordering arguments... split for now to control inheritance order...
    key: str = classyclick.Argument()
    secret: str = classyclick.Argument()
    passphrase: str = classyclick.Argument()
    exclude_zeros: bool = classyclick.Option(help='Do not report accounts/tokens with 0 balance')


@classyclick.command()
class CLI(BasicCLI, Args):
    def handle(self):
        client_option = (
            ClientOptionBuilder()
            .set_key(self.key)
            .set_secret(self.secret)
            .set_passphrase(self.passphrase)
            .set_spot_endpoint(GLOBAL_API_ENDPOINT)
            .set_futures_endpoint(GLOBAL_FUTURES_API_ENDPOINT)
            .set_broker_endpoint(GLOBAL_BROKER_API_ENDPOINT)
            .set_transport_option(TransportOptionBuilder().build())
            .build()
        )
        client = DefaultClient(client_option)
        prices = client.rest_service().get_spot_service().get_market_api().get_fiat_price(GetFiatPriceReq())
        accounts = (
            client.rest_service()
            .get_account_service()
            # TODO: add margin and futures
            .get_account_api()
            .get_spot_account_list(GetSpotAccountListReq())
        )
        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'USD',
            },
        }
        accum = {}

        for account in accounts.common_response.data:
            if account['balance'] == '0' and self.exclude_zeros:
                continue
            accum[account['currency']] = float(accum.get(account['currency'], 0)) + float(account['balance'])

        current_page = 1
        accum_sub = {}
        while True:
            sub_accounts = (
                client.rest_service()
                .get_account_service()
                .get_sub_account_api()
                .get_spot_sub_account_list_v2(GetSpotSubAccountListV2Req(currentPage=current_page, pageSize=100))
            )
            for sub in sub_accounts.items:
                for subs in (sub.main_accounts, sub.trade_accounts, sub.margin_accounts):
                    for account in subs:
                        kn = account.currency
                        kv = float(account.balance)
                        accum[kn] = float(accum.get(kn, 0)) + kv
                        price = float(getattr(prices, kn, 0))
                        accum_sub[sub.sub_name] = accum_sub.get(sub.sub_name, 0) + price * kv

            if sub_accounts.total_page <= current_page:
                break
            current_page += 1

        for k, v in accum.items():
            k = k.lower()
            price = float(getattr(prices, k, 0))
            usd = price * float(v)
            print(k, v, usd)
            hass_data['state'] += usd
            hass_data['attributes'][k] = v
            hass_data['attributes'][f'{k}_val'] = usd

        for k, v in accum_sub.items():
            k = f'sub_{k}'
            print(k, v)
            hass_data['attributes'][k] = v

        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI.click()
