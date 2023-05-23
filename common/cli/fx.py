import requests


class CryptoFXMixin:
    def get_crypto_fx_rate(self, tokens, currencies=['usd']):
        """
        Get latest exchange rates for these tokens
        """
        return self.get_crypto_fx_rate_coingecko(tokens, currencies=currencies)

    def get_crypto_fx_rate_coingecko(self, tokens, currencies=['usd']):
        """
        Get latest exchange rates for these tokens from coingecko API
        """
        single_token = True
        single_currency = True
        if isinstance(tokens, (list, tuple)):
            single_token = len(tokens) == 1
            tokens = ','.join(tokens)
        if isinstance(currencies, (list, tuple)):
            single_currency = len(currencies) == 1
            currencies = ','.join(currencies)
        r = requests.get(
            'https://api.coingecko.com/api/v3/simple/price', params={'ids': tokens, 'vs_currencies': currencies}
        )
        r.raise_for_status()
        data = r.json()
        if single_currency:
            # flatten currencies
            for token in list(data.keys()):
                data[token] = data[token][currencies]
        if single_token:
            # flatten data
            data = data[tokens]
        return data

    def get_crypto_fx_rate_coinmarketcap(self, slugs):
        """
        Get latest exchange rates for these slugs from coinmarketcap (private but open) API

        slug is not the token symbol, look up your tokens in coinmarket web UI and the slug will be in the URL
        eg: ...../avalanche/ (for AVAX)
        """
        if not isinstance(slugs, (list, tuple)):
            slugs = [slugs]

        all_data = {}
        for slug in slugs:
            r = requests.get(
                'https://api.coinmarketcap.com/aggr/v3/web/coin-detail', params={'slug': slug, 'langCode': 'en'}
            )
            r.raise_for_status()
            data = r.json()
            all_data[slug] = data['data']['detail']['statistics']['price']

        if len(slugs) == 1:
            # flatten data
            return all_data[slugs[0]]
        return all_data
