import requests


class CryptoFXMixin:
    def get_crypto_fx_rate(self, tokens, currencies=['usd'], coinmarketcap_slugs=None):
        """
        Get latest exchange rates for these tokens

        Uses coingecko API by default but will fallback to coinmarketcap API if first is available (and coinmarketcap_slugs are specified)
        """
        try:
            return self.get_crypto_fx_rate_coingecko(tokens, currencies=currencies)
        except requests.exceptions.HTTPError:
            if coinmarketcap_slugs is None:
                raise
            if isinstance(tokens, (list, tuple)):
                if not isinstance(coinmarketcap_slugs, dict):
                    # if multiple tokens, coinmarketcap_slugs should be a dictionary to map coingecko token with coinmarketcap slug (for consistent result keys)
                    raise Exception('`coinmarketcap_slugs` must be a dicitionary when multiple tokens are used')
                slugs = list(coinmarketcap_slugs.values())
            else:
                if not isinstance(coinmarketcap_slugs, str):
                    raise Exception('`coinmarketcap_slugs` must be a str when a single token is used')
                slugs = [coinmarketcap_slugs]

            r = self.get_crypto_fx_rate_coinmarketcap(slugs)
            if len(slugs) > 1:
                # re-map for result consistency
                for k, v in coinmarketcap_slugs.items():
                    if k != v:
                        r[k] = r[v]
            return r

    def get_crypto_fx_rate_coingecko(self, tokens, currencies=['usd']):
        """
        Get latest exchange rates for these tokens from coingecko API

        `tokens` should be an `API id` (visible in the web UI) or a list of those
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
            try:
                all_data[slug] = data['data']['detail']['statistics']['price']
            except KeyError:
                raise Exception(f'{slug} not found')

        if len(slugs) == 1:
            # flatten data
            return all_data[slugs[0]]
        return all_data
