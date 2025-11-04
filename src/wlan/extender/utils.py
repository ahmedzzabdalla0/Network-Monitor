import logging
from typing import List

import pandas as pd

from wlan.enums.shared_enum import DeviceSource
from wlan.exceptions import DataParsingError, EncryptionError
from wlan.managers import ConfigManager
from wlan.mappers import TLEXTENDER_COLUMNS_MAP
from wlan.schemas import StandardColumns as S
from wlan.utils import DataframeUtils

from .constants import TLExtenderLogin

logger = logging.getLogger(__name__)


class TLExtenderUtils:

    @staticmethod
    def su_encrypt(e: str, t: str = None, r: str = None) -> str:
        """Encrypt string using custom algorithm.

        Args:
            e: String to encrypt
            t: Encryption key (default from TLExtenderLogin)
            r: Encryption table (default from TLExtenderLogin)

        Returns:
            str: Encrypted string

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            t = t or TLExtenderLogin.T_SU_ENCRYPT
            r = r or TLExtenderLogin.R_SU_ENCRYPT

            if not e:
                raise ValueError("Input string cannot be empty")
            if not t or not r:
                raise ValueError("Encryption parameters cannot be empty")

            n = []
            o, l, u = len(e), len(t), len(r)
            d = max(o, l)

            for h in range(d):
                s = 187 if o <= h else ord(e[h])
                a = 187 if l <= h else ord(t[h])
                n.append(r[(s ^ a) % u])

            return ''.join(n)

        except Exception as ex:
            logger.error(f"Encryption failed: {ex}")
            raise EncryptionError(f"Failed to encrypt string: {ex}") from ex

    @staticmethod
    def id_encrypt(text_response: str, password: str) -> str:
        """Encrypt ID using response and password.

        Args:
            text_response: Response text containing auth tokens
            password: Password for encryption

        Returns:
            str: Encrypted ID

        Raises:
            EncryptionError: If ID encryption fails
        """
        try:
            if not text_response or not password:
                raise ValueError("Response and password cannot be empty")

            lines = text_response.splitlines()
            if len(lines) < 5:
                raise ValueError(
                    f"Invalid response format: expected at least 5 lines, got {len(lines)}")

            pre_auth = TLExtenderUtils.su_encrypt(password)
            auth3, auth4 = lines[3:5]

            if not auth3 or not auth4:
                raise ValueError("Auth tokens cannot be empty")

            return TLExtenderUtils.su_encrypt(auth3, pre_auth, auth4)

        except ValueError as ex:
            logger.error(f"ID encryption validation failed: {ex}")
            raise EncryptionError(
                f"Invalid data for ID encryption: {ex}") from ex
        except Exception as ex:
            logger.error(f"ID encryption failed: {ex}")
            raise EncryptionError(f"Failed to encrypt ID: {ex}") from ex

    @staticmethod
    def devices_handle(text_response: str) -> pd.DataFrame:
        """Parse and process devices response.

        Args:
            text_response: Response text containing device data

        Returns:
            pd.DataFrame: DataFrame with device information

        Raises:
            DataParsingError: If parsing fails
        """
        try:
            if not text_response or not text_response.strip():
                logger.warning("Empty response received for devices")
                return pd.DataFrame(columns=ConfigManager.get("main.columns", []))

            excluded_ips: List = ConfigManager.get("extender.excluded_ips", [])
            excluded_macs: List = ConfigManager.get(
                "extender.excluded_macs", [])
            filtered_columns: List = ConfigManager.get("main.columns", [])

            data = {}

            for line in text_response.strip().splitlines():
                parts = line.strip().split(" ", 2)
                if len(parts) == 3:
                    key, idx, val = parts
                    data.setdefault(key, {})[idx] = val

            if not data:
                logger.warning("No valid data found in response")
                return pd.DataFrame(columns=filtered_columns)

            rows = [{k: (data[k].get(i) if isinstance(data[k], dict) else data[k])
                    for k in data} for i in data.get("ip", {}).keys()]

            df = pd.DataFrame(rows)

            if df.empty:
                logger.info("No devices found in response")
                return pd.DataFrame(columns=filtered_columns)

            df.rename(columns=TLEXTENDER_COLUMNS_MAP, inplace=True)

            # Normalize MAC addresses
            if S.MAC_ADDRESS in df.columns:
                df[S.MAC_ADDRESS] = df[S.MAC_ADDRESS].str.lower().str.replace("-", ":")

            # Filter active devices only
            if S.ACTIVE in df.columns:
                df = df[df[S.ACTIVE] == '1']

            # Exclude specified IPs and MACs
            df = DataframeUtils.exclude_rows(df, S.IP_ADDRESS, excluded_ips)
            df = DataframeUtils.exclude_rows(df, S.MAC_ADDRESS, excluded_macs)

            # Add default values to columns
            df[S.SOURCE] = DeviceSource.EXTENDER.value
            df[S.SIGNAL_LEVEL] = '0'

            # Filter columns
            existing_columns = [
                col for col in filtered_columns if col in df.columns]

            logger.info(f"Successfully parsed {len(df)} devices")
            return df[existing_columns]

        except Exception as ex:
            logger.error(f"Failed to parse devices response: {ex}")
            raise DataParsingError(
                f"Failed to process devices data: {ex}") from ex
