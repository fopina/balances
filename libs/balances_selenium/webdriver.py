from pathlib import Path

from selenium import webdriver
from selenium.common import exceptions
from selenium.webdriver.chrome.service import Service


class ChromiumHelperMixin:
    """Shared Chromium setup decisions for local and remote Selenium drivers."""

    def hide_selenium(self, options: webdriver.ChromeOptions):
        """Apply common flags that make automation less obvious to websites.

        Several banking/exchange sites treat Selenium-specific Chrome switches
        as suspicious. Keeping all of these mitigations together ensures local
        and grid drivers present the same browser profile.
        """
        # hide selenium! all possible flags found online :shrug:
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-search-engine-choice-screen')
        options.add_argument('--lang=en-US,en')
        options.add_argument('--window-size=1366,900')
        options.add_experimental_option(
            'prefs',
            {
                'credentials_enable_service': False,
                'intl.accept_languages': 'en-US,en',
                'profile.password_manager_enabled': False,
            },
        )

    def go_headless(self, options: webdriver.ChromeOptions):
        """Configure Chrome for unattended/container-friendly execution.

        The GPU, sandbox, and shared-memory flags trade browser hardening for
        reliability in Docker-style environments where those resources are often
        missing or too small. ``start-maximized`` gives pages a desktop viewport
        even when no visible window exists.
        """
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('start-maximized')

    def hide_selenium_runtime(self):
        """Patch common ChromeDriver signals before page JavaScript runs."""
        self.execute_cdp_cmd(
            'Page.addScriptToEvaluateOnNewDocument',
            {
                'source': r"""
(() => {
  const nativeToString = Function.prototype.toString;
  const nativeStrings = new WeakMap();
  const markNative = (fn, name) => {
    try {
      nativeStrings.set(fn, `function ${name || fn.name || ''}() { [native code] }`);
    } catch (_) {}
    return fn;
  };
  const nativeFunctionToString = markNative(function toString() {
    if (nativeStrings.has(this)) {
      return nativeStrings.get(this);
    }
    return nativeToString.call(this);
  }, 'toString');
  try {
    Object.defineProperty(Function.prototype, 'toString', {
      configurable: true,
      writable: true,
      value: nativeFunctionToString,
    });
  } catch (_) {}

  const define = (target, property, getter) => {
    try {
      Object.defineProperty(target, property, { configurable: true, get: markNative(getter, `get ${property}`) });
    } catch (_) {}
  };

  define(Navigator.prototype, 'webdriver', () => undefined);
  define(navigator, 'webdriver', () => undefined);
  define(navigator, 'vendor', () => 'Google Inc.');
  define(navigator, 'languages', () => ['en-US', 'en']);
  define(navigator, 'hardwareConcurrency', () => 8);
  define(navigator, 'deviceMemory', () => 8);
  define(navigator, 'maxTouchPoints', () => 0);
  define(navigator, 'pdfViewerEnabled', () => true);
  define(navigator, 'userAgentData', () => ({
    brands: [
      { brand: 'Chromium', version: '141' },
      { brand: 'Google Chrome', version: '141' },
      { brand: 'Not:A-Brand', version: '24' },
    ],
    mobile: false,
    platform: 'macOS',
    getHighEntropyValues: markNative(async function getHighEntropyValues(hints) {
      const values = {
        architecture: 'x86',
        bitness: '64',
        brands: [
          { brand: 'Chromium', version: '141' },
          { brand: 'Google Chrome', version: '141' },
          { brand: 'Not:A-Brand', version: '24' },
        ],
        fullVersionList: [
          { brand: 'Chromium', version: '141.0.7390.76' },
          { brand: 'Google Chrome', version: '141.0.7390.76' },
          { brand: 'Not:A-Brand', version: '24.0.0.0' },
        ],
        mobile: false,
        model: '',
        platform: 'macOS',
        platformVersion: '13.6.6',
        uaFullVersion: '141.0.7390.76',
        wow64: false,
      };
      return Object.fromEntries((hints || []).map((hint) => [hint, values[hint]]));
    }, 'getHighEntropyValues'),
    toJSON: markNative(function toJSON() {
      return {
      brands: [
        { brand: 'Chromium', version: '141' },
        { brand: 'Google Chrome', version: '141' },
        { brand: 'Not:A-Brand', version: '24' },
      ],
      mobile: false,
      platform: 'macOS',
      };
    }, 'toJSON'),
  }));
  const makePluginArray = () => {
    const plugins = [
      { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
      { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
      { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' },
    ];
    const pluginArray = {
      length: plugins.length,
      item: markNative(function item(index) { return plugins[index] || null; }, 'item'),
      namedItem: markNative(function namedItem(name) {
        return plugins.find((plugin) => plugin.name === name) || null;
      }, 'namedItem'),
      refresh: markNative(function refresh() {}, 'refresh'),
    };
    plugins.forEach((plugin, index) => {
      pluginArray[index] = plugin;
      pluginArray[plugin.name] = plugin;
    });
    Object.defineProperty(pluginArray, Symbol.toStringTag, { value: 'PluginArray' });
    return pluginArray;
  };
  const makeMimeTypeArray = () => {
    const mimeTypes = [
      { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
      { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
    ];
    const mimeTypeArray = {
      length: mimeTypes.length,
      item: markNative(function item(index) { return mimeTypes[index] || null; }, 'item'),
      namedItem: markNative(function namedItem(name) {
        return mimeTypes.find((mimeType) => mimeType.type === name) || null;
      }, 'namedItem'),
    };
    mimeTypes.forEach((mimeType, index) => {
      mimeTypeArray[index] = mimeType;
      mimeTypeArray[mimeType.type] = mimeType;
    });
    Object.defineProperty(mimeTypeArray, Symbol.toStringTag, { value: 'MimeTypeArray' });
    return mimeTypeArray;
  };
  define(navigator, 'plugins', makePluginArray);
  define(navigator, 'mimeTypes', makeMimeTypeArray);
  define(window, 'outerWidth', () => window.innerWidth);
  define(window, 'outerHeight', () => window.innerHeight + 85);

  if (!window.chrome) {
    window.chrome = {};
  }
  window.chrome.app = window.chrome.app || {
    InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
    RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
    getDetails: markNative(function getDetails() { return null; }, 'getDetails'),
    getIsInstalled: markNative(function getIsInstalled() { return false; }, 'getIsInstalled'),
    runningState: markNative(function runningState() { return 'cannot_run'; }, 'runningState'),
  };
  window.chrome.csi = window.chrome.csi || markNative(function csi() {
    return {
    onloadT: Date.now(),
    pageT: Date.now() - performance.timing.navigationStart,
    startE: performance.timing.navigationStart,
    tran: 15,
    };
  }, 'csi');
  window.chrome.loadTimes = window.chrome.loadTimes || markNative(function loadTimes() {
    return {
    commitLoadTime: performance.timing.responseStart / 1000,
    connectionInfo: 'h2',
    finishDocumentLoadTime: performance.timing.domContentLoadedEventEnd / 1000,
    finishLoadTime: performance.timing.loadEventEnd / 1000,
    firstPaintAfterLoadTime: 0,
    firstPaintTime: performance.timing.responseStart / 1000,
    navigationType: 'Other',
    npnNegotiatedProtocol: 'h2',
    requestTime: performance.timing.navigationStart / 1000,
    startLoadTime: performance.timing.navigationStart / 1000,
    wasAlternateProtocolAvailable: false,
    wasFetchedViaSpdy: true,
    wasNpnNegotiated: true,
    };
  }, 'loadTimes');
  window.chrome.runtime = window.chrome.runtime || {};
  window.chrome.runtime.PlatformArch = window.chrome.runtime.PlatformArch || {
    ARM: 'arm',
    ARM64: 'arm64',
    MIPS: 'mips',
    MIPS64: 'mips64',
    X86_32: 'x86-32',
    X86_64: 'x86-64',
  };
  window.chrome.runtime.PlatformNaclArch = window.chrome.runtime.PlatformNaclArch || {
    ARM: 'arm',
    MIPS: 'mips',
    MIPS64: 'mips64',
    X86_32: 'x86-32',
    X86_64: 'x86-64',
  };
  window.chrome.runtime.PlatformOs = window.chrome.runtime.PlatformOs || {
    ANDROID: 'android',
    CROS: 'cros',
    LINUX: 'linux',
    MAC: 'mac',
    OPENBSD: 'openbsd',
    WIN: 'win',
  };
  window.chrome.runtime.RequestUpdateCheckStatus = window.chrome.runtime.RequestUpdateCheckStatus || {
    NO_UPDATE: 'no_update',
    THROTTLED: 'throttled',
    UPDATE_AVAILABLE: 'update_available',
  };

  const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
  if (originalQuery) {
    window.navigator.permissions.query = markNative(function query(parameters) {
      return parameters && parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery.call(window.navigator.permissions, parameters);
    }, 'query');
  }

  for (const key of Object.keys(window)) {
    if (/^(cdc_|webdriver|__webdriver|selenium|callPhantom|_phantom)/i.test(key)) {
      try {
        delete window[key];
      } catch (_) {}
    }
  }

  for (const key of Object.keys(document)) {
    if (/^(cdc_|webdriver|__webdriver|selenium)/i.test(key)) {
      try {
        delete document[key];
      } catch (_) {}
    }
  }

  const webglVendor = 'Intel Inc.';
  const webglRenderer = 'Intel Iris OpenGL Engine';
  const patchWebGL = (prototype) => {
    if (!prototype || !prototype.getParameter) {
      return;
    }
    const getParameter = prototype.getParameter;
    prototype.getParameter = markNative(function getParameter(parameter) {
      if (parameter === 37445) {
        return webglVendor;
      }
      if (parameter === 37446) {
        return webglRenderer;
      }
      return getParameter.call(this, parameter);
    }, 'getParameter');
  };
  patchWebGL(window.WebGLRenderingContext && window.WebGLRenderingContext.prototype);
  patchWebGL(window.WebGL2RenderingContext && window.WebGL2RenderingContext.prototype);
})();
""",
            },
        )

    def navigator_platform(self, user_agent: str):
        """Return a navigator.platform value consistent with the UA string."""
        if 'Macintosh' in user_agent:
            return 'MacIntel'
        if 'Windows' in user_agent:
            return 'Win32'
        if 'Android' in user_agent:
            return 'Linux armv8l'
        if 'Linux' in user_agent:
            return 'Linux x86_64'
        return None

    def user_agent_platform(self, user_agent: str):
        """Return a UA client hints platform value consistent with the UA."""
        if 'Macintosh' in user_agent:
            return 'macOS'
        if 'Windows' in user_agent:
            return 'Windows'
        if 'Android' in user_agent:
            return 'Android'
        if 'Linux' in user_agent:
            return 'Linux'
        return None

    def user_agent_metadata(self, user_agent: str):
        """Build minimal UA client hints matching the sanitized browser UA."""
        try:
            full_version = user_agent.split('Chrome/')[1].split(' ')[0]
            major_version = full_version.split('.')[0]
        except IndexError:
            return None

        platform = self.user_agent_platform(user_agent)
        metadata = {
            'architecture': 'arm' if 'Android' in user_agent else 'x86',
            'brands': [
                {'brand': 'Chromium', 'version': major_version},
                {'brand': 'Google Chrome', 'version': major_version},
                {'brand': 'Not:A-Brand', 'version': '24'},
            ],
            'fullVersion': full_version,
            'fullVersionList': [
                {'brand': 'Chromium', 'version': full_version},
                {'brand': 'Google Chrome', 'version': full_version},
                {'brand': 'Not:A-Brand', 'version': '24.0.0.0'},
            ],
            'mobile': 'Android' in user_agent,
            'model': '',
            'platform': platform or 'Unknown',
            'platformVersion': '',
        }
        return metadata

    def sanitized_user_agent(self):
        """Return Chromium's real user agent without the headless marker."""
        version = self.execute_cdp_cmd('Browser.getVersion', {})
        return version['userAgent'].replace('HeadlessChrome/', 'Chrome/')

    def set_user_agent(self, user_agent: str | None = None):
        """Override the runtime user agent through Chrome DevTools Protocol.

        When no explicit value is supplied, keep the browser's actual UA and
        only remove Chrome's headless marker. That keeps the UA aligned with
        other browser fingerprinting surfaces such as client hints and feature
        support.
        """
        user_agent = user_agent or self.sanitized_user_agent()
        args = {
            'acceptLanguage': 'en-US,en;q=0.9',
            'userAgent': user_agent,
        }
        metadata = self.user_agent_metadata(user_agent)
        if metadata is not None:
            args['userAgentMetadata'] = metadata
        platform = self.navigator_platform(user_agent)
        if platform:
            args['platform'] = platform
        try:
            self.execute_cdp_cmd('Network.setUserAgentOverride', args)
        except exceptions.InvalidArgumentException:
            args.pop('userAgentMetadata', None)
            self.execute_cdp_cmd('Network.setUserAgentOverride', args)

    def init_options_in_driver_kwargs(self, extra_driver_kwargs: dict):
        """Extract or create Chrome options before constructing a driver.

        Selenium constructors want ``options`` as a named argument, while callers
        may pass additional driver kwargs. Popping here avoids sending duplicate
        ``options`` later and asserts early if a caller provides the wrong type.
        """
        options = extra_driver_kwargs.pop('options', webdriver.ChromeOptions())
        assert isinstance(options, webdriver.ChromeOptions)
        return options


class MyRemoteDriver(webdriver.Remote, ChromiumHelperMixin):
    """Remote Selenium driver with the same Chromium defaults as local runs."""

    def __init__(
        self, command_executor='http://127.0.0.1:4444', headless=False, user_agent=None, **extra_driver_kwargs
    ):
        """Start a remote Chromium session with scraper-friendly defaults.

        The grid path mirrors ``MyDriver`` as closely as possible so switching
        between local debugging and Selenium Grid does not change scraper
        behavior beyond where the browser is hosted.
        """
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)
        if headless:
            self.go_headless(options)
        super().__init__(command_executor, options=options, **extra_driver_kwargs)
        self.hide_selenium_runtime()
        self.set_user_agent(user_agent)

    def execute_cdp_cmd(self, cmd: str, cmd_args: dict):
        """Send a CDP command through Selenium Remote.

        ``webdriver.Remote`` does not expose Chrome's helper directly, so the CDP
        endpoint is registered on the command executor before dispatching. This
        keeps user-agent override support available for grid sessions too.
        """
        # copied from ChromiumRemoteConnection
        self.command_executor._commands['executeCdpCommand'] = ('POST', '/session/$sessionId/goog/cdp/execute')
        return self.execute('executeCdpCommand', {'cmd': cmd, 'params': cmd_args})['value']


class MyDriver(webdriver.Chrome, ChromiumHelperMixin):
    """Local Chromium driver used by scrapers when no Selenium Grid is set."""

    def __init__(self, headless=False, remote_debug_port=None, user_agent=None, **extra_driver_kwargs):
        """Start a local Chromium session with optional debugging hooks.

        A locally installed Chromium.app is preferred on macOS development
        machines to avoid depending on whichever Chrome binary Selenium finds.
        The remote debugging port is only added when requested so normal
        automated runs do not expose an unnecessary debugging endpoint.
        """
        options = self.init_options_in_driver_kwargs(extra_driver_kwargs)
        self.hide_selenium(options)

        if Path('/Applications/Chromium.app/Contents/MacOS/Chromium').exists():
            # for dev environment
            options.binary_location = '/Applications/Chromium.app/Contents/MacOS/Chromium'

        chrome_path = Path(
            '/Users/fopina/.cache/selenium/chrome/mac-arm64/141.0.7390.76/'
            'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
        )
        chromedriver_path = Path('/Users/fopina/.cache/selenium/chromedriver/mac-arm64/141.0.7390.76/chromedriver')
        if chrome_path.exists() and chromedriver_path.exists():
            options.binary_location = str(chrome_path)
            extra_driver_kwargs.setdefault('service', Service(executable_path=str(chromedriver_path)))

        if headless:
            self.go_headless(options)
        if remote_debug_port:
            options.add_argument(f'--remote-debugging-port={remote_debug_port}')
        super().__init__(options=options, **extra_driver_kwargs)
        self.hide_selenium_runtime()
        self.set_user_agent(user_agent)


exceptions.WebDriverException.__str__ = lambda x: f'Message: {x.msg}\n'
