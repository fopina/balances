from dataclasses import dataclass

import classyclick
import onetimepass


@dataclass
class OTPMixin:
    otp: str = classyclick.Option('-o', help='OTP code')
    otp_secret: str = classyclick.Option('-s', help='OTP secret (to generate code)')

    def otp_holder(self):
        if self.otp or self.otp_secret:
            return _Holder(self.otp, self.otp_secret)

    def get_otp_code(self):
        holder = self.otp_holder()
        if holder is not None:
            return holder()


class _Holder:
    def __init__(self, otp, otp_secret):
        self._otp = otp
        self._otp_secret = otp_secret

    def __call__(self, *args, **kwds):
        if self._otp_secret:
            return onetimepass.get_totp(self._otp_secret, **kwds)
        return self._otp
