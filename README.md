# balances
random scrapers of crypto/banking/stocks balances/portfolios

All of these are designed thinking of: scrape data and push to [home-assistant](https://www.home-assistant.io/).

For anyone looking for the same, they're plug and play. For the rest, maybe the scraping code is useful.

Check each module for documentation (comments on top) on how to use it.

## Scrapers

When using a Selenium-dependent scraper (such as [Fidelity](fidelity.py)) in a docker image, you need to run selenium image separately as it is not part of the scraper image:

```
make selenium
```

Now, run the scraper image with `docker run ... --link selenium_balances SCRAPER_IMAGE ... --grid http://selenium_balances:4444 ...`
If you need to debug browser interaction, just open http://localhost:7900.

### Crypto

* ~~[Anchor](archive/anchor.py) - old (and failed) Terra project / [Anchorprotocol](https://app.anchorprotocol.com/)~~
* ~~[Luna20](archive/luna20.py) - [Terra 2.0](https://station.terra.money/) project~~
* ~~[Celsius](archive/celsius.py) - [Celsius](https://celsius.network/) (RIP)~~
* [Crypto.com](cryptocom/main.py) - [website](https://crypto.com/) but this is for the `app` account, not the exchange
* [Kucoin](kucoin/main.py) - [website](https://kucoin.com/)
* ~~[Plutus](archive/plutus.py) - [website](https://plutus.it/)~~

### Stocks

* [Degiro](degiro.py) - [website](https://www.degiro.nl/)
* [Interactive Brokers](ibfetch.py) - [website](https://www.interactivebrokers.co.uk/)
* ~~[Fidelity](fidelity.py) - [website](https://nb.fidelity.com/)~~
  * No point fighting Akamai bot detection for a portfolio that changes so seldomly: it can easily be replaced with static inventory with public quotes

### Banking

* ~~[CaixaBreak](archive/caixabreak.py) - Portuguese [meal allowance debit card](https://www.cgd.pt/Particulares/Cartoes/Cartoes-Pre-pagos/Pages/Cartao-Pre-Pago-caixa-break.aspx)~~

### Misc

* ~~[Snailtrail](archive/snailtrail.py) - snail and wallets stats for [this game](https://www.snailtrail.art/)~~
* [Finanças](financas/main.py) - Portuguese tax benefits from [efaturas](https://faturas.portaldasfinancas.gov.pt/)
