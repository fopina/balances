import requests
import re
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

from common.cli import BasicCLI

logger = logging.getLogger(__name__)


class ClientError(Exception):
    """errors raised by client validations"""


class Client(requests.Session):
    def __init__(self):
        super().__init__()
        self.headers.update({
            'User-Agent': 'Firefox'
        })
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.mount("https://", adapter)
        self.mount("http://", adapter)

    def login(self, username, password):
        r = self.get('https://www.acesso.gov.pt/jsp/loginRedirectForm.jsp?path=painelAdquirente.action&partID=EFPF')
        r.raise_for_status()
        m = re.findall(r'<input type="hidden" name="_csrf" value="(.*?)"/>', r.text)
        if not m:
            raise ClientError('failed to get csrf token')
        r = self.post(
            'https://www.acesso.gov.pt/jsp/submissaoFormularioLogin',
            data={
                'partID': 'EFPF',
                'password': password,
                'authVersion': '1',
                'username': username,
                'path': 'painelAdquirente.action',
                '_csrf': m[0],
                'selectedAuthMethod': 'N',
            }
        )
        r.raise_for_status()
        if '<div class="error-message">' in r.text:
            m = re.findall(r'<div class="error-message">(.*?)</div>', r.text)
            if m:
                raise ClientError(f'login error: {m[0]}')
            raise ClientError('login error')
        m = re.findall(r'<input type="hidden" name="(.*?)" value="(.*?)">', r.text)
        if not m:
            raise ClientError('failed to login')

        for _try in range(10):
            # flaky faturas.portaldasfinancas.gov.pt returning 404 sometimes
            # retry a few times
            r = self.post(
                'https://faturas.portaldasfinancas.gov.pt/painelAdquirente.action',
                data={
                    x: y
                    for x, y in m
                }
            )
            if r.status_code != 404:
                break
            logger.error('Failed try %d', _try)
        return self._parse_dashboard(r)
    
    def dashboard_stats(self):
        return self._parse_dashboard(
            self.get('https://faturas.portaldasfinancas.gov.pt/painelAdquirente.action')
        )
    
    def pending_invoices(self, year=None):
        n = datetime.now()
        tc = int(n.timestamp() * 1000)
        if year is None:
            year = n.year

        r = self.get(
            'https://faturas.portaldasfinancas.gov.pt/json/obterDocumentosAdquirente.action',
            params={
                'dataInicioFilter': f'{year}-01-01',
                'dataFimFilter': f'{year}-12-31',
                'estadoDocumentoFilter': 'P',
                'ambitoAquisicaoFilter': 'TODOS',
                '_': tc,
            }
        )
        r.raise_for_status()
        return r.json()['totalElementos']
    
    def _parse_dashboard(self, r):
        r.raise_for_status()
        m = re.findall(
            r'<div class="benef-icon atf atf-(.*?)"></div>'
            r'\s*<div class="benefbox1-title">\s*<div>\s*<h2>(.*?)</h2>\s*</div>\s*</div>'
            r'\s*<span class="euro-value">(.*?) &euro;</span>'
            r'\s*<p>(.*?)</p>',
            r.text,
            re.DOTALL,
        )
        data = {}
        for mm in m:
            benefit = float(mm[2].replace('.', '').replace(',', '.'))
            spent = 0
            r = re.findall(r'<span class="nowrap_text">(.*?) &euro;', mm[3])
            if r:
                spent = float(r[0].replace('.', '').replace(',', '.'))
            data[mm[0]] = (mm[1], benefit, spent)
        return data


class CLI(BasicCLI):
    def extend_parser(self, parser):
        parser.add_argument('username')
        parser.add_argument('password')
        parser.add_argument('-o', '--otp', help='OTP code')
        parser.add_argument('-s', '--otp-secret', help='OTP secret (to generate code)')
        parser.add_argument('-p', '--pin', help='use device login with this pin code (password should be device id)')
    
    def handle(self, args):
        client = Client()
        stats = client.login(args.username, args.password)
        pending = client.pending_invoices()
        print(f'Pending: {pending}')

        hass_data = {
            'state': 0,
            'attributes': {
                'unit_of_measurement': 'EUR',
                'pending': pending,
            }
        }

        for k, v in stats.items():
            hass_data['state'] += v[1]
            hass_data['attributes'][f'{k}_return'] = v[1]
            hass_data['attributes'][f'{k}_spent'] = v[2]
            print(f'{v[0]} ({k}): {v[1]} ({v[2]})')
        print(f"\nTotal: {hass_data['state']}")
        return hass_data


if __name__ == '__main__':
    CLI()()
