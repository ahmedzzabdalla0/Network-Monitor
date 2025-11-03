from .constants import TLExtenderConstants


class TLExtenderUtils:

    @staticmethod
    def su_encrypt(e: str, t: str = None, r: str = None) -> str:
        if r is None:
            r = TLExtenderConstants.R_SU_ENCRYPT
        if t is None:
            t = TLExtenderConstants.T_SU_ENCRYPT
        n = []
        o, l, u = len(e), len(t), len(r)
        d = max(o, l)
        for h in range(d):
            s = 187 if o <= h else ord(e[h])
            a = 187 if l <= h else ord(t[h])
            n.append(r[(s ^ a) % u])
        return ''.join(n)
