from dataclasses import dataclass

import classyclick
import onetimepass


@dataclass
class OTPMixin:
    """Add optional one-time-password support to a CLI command."""

    otp: str = classyclick.Option('-o', help='OTP code')
    otp_secret: str = classyclick.Option('-s', help='OTP secret (to generate code)')

    def otp_holder(self):
        """Return a callable OTP provider only when OTP input was configured.

        Scrapers can treat static codes and generated TOTP values the same way,
        while commands that do not need OTP can skip the flow by receiving
        ``None``.
        """
        if self.otp or self.otp_secret:
            return _Holder(self.otp, self.otp_secret)

    def get_otp_code(self):
        """Resolve the current OTP code, if one is available.

        The holder is invoked lazily so TOTP values are generated as close as
        possible to form submission instead of at CLI startup.
        """
        holder = self.otp_holder()
        if holder is not None:
            return holder()


class _Holder:
    """Callable wrapper that gives explicit OTP codes and TOTP secrets one API."""

    def __init__(self, otp, otp_secret):
        """Store the mutually-compatible OTP inputs.

        Both values are accepted because some services require a manually
        supplied code, while others can be automated from a stored TOTP seed.
        """
        self._otp = otp
        self._otp_secret = otp_secret

    def __call__(self, *args, **kwds):
        """Return a generated TOTP when a secret exists, otherwise the raw code.

        Secrets take precedence because they produce fresh codes and avoid using
        a stale manually supplied value when both options are accidentally set.
        """
        if self._otp_secret:
            return onetimepass.get_totp(self._otp_secret, **kwds)
        return self._otp
