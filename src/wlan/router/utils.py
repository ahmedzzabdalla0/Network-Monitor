import base64
import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from Crypto.Cipher import AES, PKCS1_v1_5
from Crypto.Cipher._mode_cbc import CbcMode
from Crypto.PublicKey import RSA
from Crypto.Util.Padding import pad, unpad

from wlan.managers import ConfigManager
from wlan.mappers import HOST_COLUMNS_MAP, WLAN_COLUMNS_MAP
from wlan.schemas import HostColumns as H
from wlan.schemas import StandardColumns as S
from wlan.schemas import WlanColumns
from wlan.utils import DataframeUtils

from .exceptions import DataParsingError, EncryptionError

logger = logging.getLogger(__name__)

Content = Union[Dict, str]
KeyIV = Tuple[str, str]


class ZyxelGatewayUtils:
    """
    Static class providing encryption and decryption utilities 
    specifically tailored for the Zyxel router's login mechanism.
    """

    @staticmethod
    def generate_aes_key_iv() -> KeyIV:
        """
        Generates a base64-encoded 32-byte key and 32-byte IV.

        Returns:
            Tuple of (key, iv) as base64-encoded strings.

        Raises:
            EncryptionError: If random generation fails.
        """
        try:
            def gen() -> str:
                return base64.b64encode(os.urandom(32)).decode()
            return gen(), gen()
        except Exception as e:
            logger.error(f"Failed to generate AES key/IV: {e}")
            raise EncryptionError(f"Failed to generate AES key/IV: {e}") from e

    @staticmethod
    def stringify_content(content: Content) -> str:
        """
        Converts dict content to a compact JSON string.

        Args:
            content: Dictionary or string to stringify.

        Returns:
            JSON string representation.
        """
        if isinstance(content, dict):
            return json.dumps(content, separators=(',', ':'))
        return str(content)

    @staticmethod
    def encrypt_aes(key: str, iv: str, content: Content) -> str:
        """
        Encrypts content using AES-256-CBC and returns a base64 string.

        Args:
            key: Base64-encoded encryption key.
            iv: Base64-encoded initialization vector.
            content: Data to encrypt (dict or string).

        Returns:
            Base64-encoded encrypted data.

        Raises:
            EncryptionError: If encryption fails.
        """
        try:
            key_bytes = base64.b64decode(key)
            iv_bytes = base64.b64decode(iv)

            cipher: CbcMode = AES.new(
                key_bytes, AES.MODE_CBC, iv=iv_bytes[:AES.block_size])

            data_str = ZyxelGatewayUtils.stringify_content(content)
            data_padded = pad(data_str.encode('utf-8'),
                              AES.block_size, style='pkcs7')

            encrypted_data = cipher.encrypt(data_padded)
            return base64.b64encode(encrypted_data).decode()

        except Exception as e:
            logger.error(f"AES encryption failed: {e}")
            raise EncryptionError(f"AES encryption failed: {e}") from e

    @staticmethod
    def decrypt_aes(key: str, iv: str, encrypted_base64: str) -> Content:
        """
        Decrypts a base64 string using AES and attempts to decode it as JSON.

        Args:
            key: Base64-encoded decryption key.
            iv: Base64-encoded initialization vector.
            encrypted_base64: Base64-encoded encrypted data.

        Returns:
            Decrypted content as dict or string.

        Raises:
            EncryptionError: If decryption fails.
            DataParsingError: If JSON parsing fails.
        """
        try:
            key_bytes = base64.b64decode(key)
            iv_bytes = base64.b64decode(iv)
            encrypted_data = base64.b64decode(encrypted_base64)

            cipher = AES.new(key_bytes, AES.MODE_CBC,
                             iv=iv_bytes[:AES.block_size])
            decrypted_padded = cipher.decrypt(encrypted_data)

            decrypted = unpad(decrypted_padded, AES.block_size, style='pkcs7')
            decrypted_text = decrypted.decode('utf-8')

            try:
                return json.loads(decrypted_text)
            except json.JSONDecodeError as e:
                logger.warning(f"Decrypted content is not valid JSON: {e}")
                raise DataParsingError(
                    f"Cannot parse decrypted content as JSON: {e}") from e

        except (ValueError, KeyError) as e:
            logger.error(f"AES decryption failed: {e}")
            raise EncryptionError(f"AES decryption failed: {e}") from e

    @staticmethod
    def encrypt_rsa(public_key_pem: str, message: str) -> str:
        """
        Encrypts a message using RSA (PKCS1_v1_5) and returns a base64 string.

        Args:
            public_key_pem: PEM-formatted public key.
            message: Message to encrypt (typically the AES Key).

        Returns:
            Base64-encoded encrypted message.

        Raises:
            EncryptionError: If RSA encryption fails.
        """
        try:
            key = RSA.import_key(public_key_pem)
            cipher = PKCS1_v1_5.new(key)
            ciphertext = cipher.encrypt(message.encode('utf-8'))
            return base64.b64encode(ciphertext).decode()
        except Exception as e:
            logger.error(f"RSA encryption failed: {e}")
            raise EncryptionError(f"RSA encryption failed: {e}") from e

    @staticmethod
    def encode_password(password: str) -> str:
        """
        Encodes a password using base64 encoding.

        Args:
            password: Plain text password.

        Returns:
            Base64-encoded password string.
        """
        return base64.b64encode(password.encode()).decode()

    @staticmethod
    def create_post_payload(encrypted_content: str, key: str, iv: str) -> str:
        """
        Constructs the final JSON payload for the login POST request.

        Args:
            encrypted_content: Base64-encoded encrypted content.
            key: Encrypted RSA.
            iv: Base64-encoded initialization vector.

        Returns:
            JSON string payload.
        """
        data = {
            "content": encrypted_content,
            "key": key,
            "iv": iv
        }
        return json.dumps(data)

    @staticmethod
    def parse_api_response(response_json: Dict, key: str) -> Content:
        """
        Extracts and decrypts the content from a router API JSON response.

        Args:
            response_json: JSON response from the router API.
            key: Base64-encoded decryption key.

        Returns:
            Decrypted content.

        Raises:
            DataParsingError: If response structure is invalid.
            EncryptionError: If decryption fails.
        """
        content = response_json.get("content")
        iv = response_json.get("iv")

        if not content or not iv:
            logger.error("API response missing 'content' or 'iv' fields")
            raise DataParsingError(
                f"Invalid API response structure. Missing required fields. Response: {response_json}"
            )

        return ZyxelGatewayUtils.decrypt_aes(key, iv, content)

    @staticmethod
    def parse_wlan(res: str, freq: Optional[int] = 2.4) -> pd.DataFrame:
        """
        Parsing the wlan response (res[0]['result']) and convert it to DataFrame (With StandardColumns).

        Args:
            res: String response of the result key (res[0]['result']).
            freq(Optional): It will added new column called 'Sourse' for all rows with that val and with prefix 'WIFI ' and posfix 'G'.

        Returns:
            Pandas DataFrame (With StandardColumns).

        Raises:
            DataParsingError: If response structure is invalid or its length not divisable by 5.
        """
        flatten_arr = re.split(r"\s+", res)
        if flatten_arr[-1] == "":
            flatten_arr.pop()
        if flatten_arr[0] == "":
            flatten_arr.pop(0)

        length = len(flatten_arr)

        if length % 5 != 0:
            raise Exception("Unexpected response structure")

        final_arr = []

        for i in range(int(length / 5)):
            final_arr.append(flatten_arr[5*i: 5*i + 5])

        df = pd.DataFrame(final_arr[1:], columns=final_arr[0])
        df[WlanColumns.MAC_ADDRESS] = df[WlanColumns.MAC_ADDRESS].str.lower()
        df[S.SOURCE] = f"WIFI {freq}G" if freq else "Router"

        return df.rename(columns=WLAN_COLUMNS_MAP)

    @staticmethod
    def hosts_handle(hosts_response: List) -> pd.DataFrame:
        hosts_df = pd.DataFrame(hosts_response)

        # Handle the device type from icons
        primary_icons = hosts_df[H.DEVICE_ICON].str.slice(1).replace("", pd.NA)
        fallback_base = hosts_df[H.ICON].str.slice(1).str.capitalize()
        fallback_icons = fallback_base.mask(
            fallback_base.str.len() <= 2,
            fallback_base.str.upper()
        )
        hosts_df[H.DEVICE_ICON] = primary_icons.fillna(fallback_icons)

        # Collect all hostnames and add them into HostName column
        hosts_df[H.CURRENT_HOST_NAME] = hosts_df[H.CURRENT_HOST_NAME].replace(
            "", pd.NA).fillna(hosts_df[H.HOST_NAME])
        hosts_df.drop(columns=[H.HOST_NAME], inplace=True)

        # Map to standard schema
        hosts_df = hosts_df.rename(
            columns={**HOST_COLUMNS_MAP, H.DEVICE_ICON: S.DEVICE_TYPE, H.CURRENT_HOST_NAME: S.HOST_NAME})

        return hosts_df

    @staticmethod
    def wlan_handle(wlan_response: List, hosts: pd.DataFrame) -> pd.DataFrame:

        excluded_macs: List = ConfigManager.get("router.excluded_macs", [])
        filtered_columns: List = ConfigManager.get("main.columns", [])

        wlan2 = ZyxelGatewayUtils.parse_wlan(wlan_response[0]['result'])
        wlan5 = ZyxelGatewayUtils.parse_wlan(wlan_response[0]['result5'], 5)

        wlan = pd.concat([wlan2, wlan5])

        devices = DataframeUtils.merge_only_on_left(wlan, hosts, S.MAC_ADDRESS)
        devices = DataframeUtils.exclude_rows(
            devices, S.MAC_ADDRESS, excluded_macs)

        existing_columns = [
            col for col in filtered_columns if col in devices.columns]

        return devices[existing_columns]
