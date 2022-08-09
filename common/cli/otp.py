import onetimepass


class OTPMixin:
    def build_parser(self):
        parser = super().build_parser()
        parser.add_argument('-o', '--otp', help='OTP code')
        parser.add_argument('-s', '--otp-secret', help='OTP secret (to generate code)')
        return parser

    def otp_holder(self, args):
        if args.otp or args.otp_secret:
            return _Holder(args.otp, args.otp_secret)


class _Holder:
    def __init__(self, otp, otp_secret):
        self._otp = otp
        self._otp_secret = otp_secret
    
    def __call__(self, *args, **kwds):
        if self._otp_secret:
            return onetimepass.get_totp(self._otp_secret, **kwds)
        return self._otp
