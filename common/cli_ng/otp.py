from dataclasses import dataclass
import onetimepass
import classyclick


@dataclass
class OTPMixin:
    otp: str = classyclick.Option('-o', help='OTP code')
    otp_secret: str = classyclick.Option('-s', help='OTP secret (to generate code)')

    def otp_holder(self):
        if self.otp or self.otp_secret:
            return _Holder(self.otp, self.otp_secret)


class _Holder:
    def __init__(self, otp, otp_secret):
        self._otp = otp
        self._otp_secret = otp_secret

    def __call__(self, *args, **kwds):
        if self._otp_secret:
            return onetimepass.get_totp(self._otp_secret, **kwds)
        return self._otp
