import os
import sys
from functools import cached_property
from pathlib import Path

import classyclick

from . import hass


class BasicCLI(classyclick.Command):
    """Base command contract shared by balance scrapers.

    Subclasses only need to implement ``handle``. This class keeps the common
    exit-code and optional Home Assistant publishing behavior in one place so
    individual scrapers stay focused on collecting their balance payload.
    """

    DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    insecure: bool = classyclick.Option(help='Skip SSL validation')
    hass: str = classyclick.Option(nargs=2, metavar='ENTITY_URL TOKEN', help='push to HASS')

    @cached_property
    def scraper_name(self):
        """Return the stable scraper identifier used in prompts and metadata.

        ``BALANCE_ENTRY`` wins when set because container entrypoints can wrap
        or reuse classes while still needing a specific published identity. The
        class file stem is the fallback because each scraper is normally kept in
        its own module and that name is stable enough for local runs.
        """
        entry = os.getenv('BALANCE_ENTRY')
        if entry:
            return entry

        import inspect

        return Path(inspect.getfile(self.__class__)).stem

    def handle(self):
        """Run the scraper and return the payload to print or publish.

        This is deliberately abstract: the base class owns orchestration, while
        each account scraper decides what data to collect and how to shape it.
        """
        raise NotImplementedError('subclass must implement this')

    def push_to_hass(self, data):
        """Publish data to Home Assistant only when the CLI option is present.

        Returning ``None`` when publishing is disabled lets ``__call__`` use the
        same expression for both print-only and publish-enabled commands. SSL
        verification follows ``--insecure`` so local/self-signed HASS endpoints
        can be used without changing scraper code.
        """
        if self.hass:
            hass.push_to_hass(self.hass[0], self.hass[1], data, verify=not self.insecure)

    def pprint(self, *args, **kwargs):
        """Pretty-print JSON-compatible data using the shared HASS formatter."""
        hass.pprint(*args, **kwargs)

    def unhandled_exception(self, exc):
        """Hook for subclasses that want to translate failures into exit codes.

        Re-raising by default keeps unexpected errors visible. Returning ``None``
        from an override intentionally maps to exit code 2 in ``__call__`` so
        callers can signal a handled-but-failed scraper without choosing a code.
        """
        raise

    def __call__(self):
        """Execute the command, publish the result, and terminate the process.

        The CLI exits with 0 when ``handle`` succeeds, or with the code returned
        by ``unhandled_exception`` when a subclass handles an error. ``sys.exit``
        is used here because classyclick command objects are process entrypoints,
        not reusable service objects.
        """
        try:
            sys.exit(self.push_to_hass(self.handle()) or 0)
        except Exception as e:
            # if unhandled_exception is not specific (None), assume 2
            r = self.unhandled_exception(e)
            if r is None:
                r = 2
            sys.exit(r)
