from typing import List

import pandas as pd

from wlan.enums.shared_enum import DeviceSource
from wlan.managers import ConfigManager
from wlan.mappers import TLEXTENDER_COLUMNS_MAP
from wlan.schemas import StandardColumns as S
from wlan.utils import DataframeUtils

from .constants import TLExtenderLogin


class TLExtenderUtils:

    @staticmethod
    def su_encrypt(e: str, t: str = None, r: str = None) -> str:
        if r is None:
            r = TLExtenderLogin.R_SU_ENCRYPT
        if t is None:
            t = TLExtenderLogin.T_SU_ENCRYPT
        n = []
        o, l, u = len(e), len(t), len(r)
        d = max(o, l)
        for h in range(d):
            s = 187 if o <= h else ord(e[h])
            a = 187 if l <= h else ord(t[h])
            n.append(r[(s ^ a) % u])
        return ''.join(n)

    @staticmethod
    def id_encrypt(text_response: str, id: str) -> str:
        auth3, auth4 = text_response.splitlines()[3:5]
        return TLExtenderUtils.su_encrypt(auth3, id, auth4)

    @staticmethod
    def devices_handle(text_response: str) -> pd.DataFrame:
        excluded_ips: List = ConfigManager.get("extender.excluded_ips", [])
        excluded_macs: List = ConfigManager.get("extender.excluded_macs", [])
        filtered_columns: List = ConfigManager.get("main.columns", [])

        data = {}

        for line in text_response.strip().splitlines():
            parts = line.strip().split(" ", 2)
            if len(parts) == 3:
                key, idx, val = parts
                data.setdefault(key, {})[idx] = val

        rows = [{k: (data[k].get(i) if isinstance(data[k], dict) else data[k])
                for k in data} for i in data.get("ip", {}).keys()]

        df = pd.DataFrame(rows)
        df.rename(columns=TLEXTENDER_COLUMNS_MAP, inplace=True)

        if not df.empty:
            df[S.MAC_ADDRESS] = df[S.MAC_ADDRESS].str.lower().str.replace("-", ":")

        df = df[df[S.ACTIVE] == '1']
        df = DataframeUtils.exclude_rows(df, S.IP_ADDRESS, excluded_ips)
        df = DataframeUtils.exclude_rows(df, S.MAC_ADDRESS, excluded_macs)

        df[S.SOURCE] = DeviceSource.EXTENDER.value

        existing_columns = [
            col for col in filtered_columns if col in df.columns]

        return df[existing_columns]
