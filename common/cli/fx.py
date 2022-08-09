import requests


class CryptoFXMixin:
    def get_crypto_fx_rate(self, tokens, currencies=['usd']):
        single_token = True
        single_currency = True
        if isinstance(tokens, (list, tuple)):
            single_token = len(tokens) == 1
            tokens = ','.join(tokens)
        if isinstance(currencies, (list, tuple)):
            single_currency = len(currencies) == 1
            currencies = ','.join(currencies)
        r = requests.get('https://api.coingecko.com/api/v3/simple/price', params={'ids': tokens, 'vs_currencies': currencies})
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
