
from datetime import datetime, timedelta
import logging

import pandas as pd
from requests import Session
from requests.exceptions import RequestException

from wlan.exceptions import (APIError, AuthenticationError, DataParsingError,
                             EncryptionError, SessionError)
from wlan.managers.config_manager import ConfigManager
from wlan.metaclasses import SingletonMeta

from .constants import TLExtenderData, TLExtenderLogin, TLExtenderURLs
from .utils import TLExtenderUtils

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


class TLExtender(metaclass=SingletonMeta):
    def __init__(self):
        self.session = Session()
        self.session_period = int(
            ConfigManager.get("extender.session_time", 3))
        self.last_refresh = None
        self.id = None

    def login(self) -> str:
        """Login to TL-Extender and get session ID.

        Returns:
            str: Session ID

        Raises:
            APIError: If login request fails
            EncryptionError: If ID encryption fails
            AuthenticationError: If login confirmation fails
        """
        # Get Public Key
        response = self.session.post(
            TLExtenderURLs.GET_TOKEN,
            headers=TLExtenderLogin.HEADERS,
            timeout=10
        )

        # Encrypt ID
        try:
            self.id = TLExtenderUtils.id_encrypt(
                response.text,
                TLExtenderLogin.PASSWORD
            )
        except Exception as e:
            logger.error(f"Failed to encrypt ID: {e}")
            raise EncryptionError(f"ID encryption failed: {e}") from e

        if not self.id:
            logger.error(f"ID encryption returned empty value")
            raise EncryptionError("ID encryption returned empty value")

        # Confirm ID
        try:
            response = self.session.post(
                TLExtenderURLs.CONFIRM_ID,
                params=dict(id=self.id),
                headers=TLExtenderLogin.HEADERS,
                timeout=10
            )
            response.raise_for_status()
        except RequestException as e:
            error_msg = f"Failed to confirm ID: {e}, Response: {response.text if 'response' in locals() else 'N/A'}"
            logger.error(error_msg)
            raise AuthenticationError(error_msg) from e

        self.last_refresh = datetime.now()
        logger.info("Successfully logged in to TL-Extender")
        return self.id

    def get_connected_devices(self) -> pd.DataFrame:
        """Get list of connected devices.

        Returns:
            pd.DataFrame: DataFrame containing device information

        Raises:
            SessionError: If not logged in
            APIError: If request fails
            DataParsingError: If response parsing fails
        """
        if not self.id or not self.last_refresh:
            raise SessionError(
                "Cannot retrieve devices: Not logged in. Call login() first.")

        now = datetime.now()
        period = now - self.last_refresh

        if period >= timedelta(minutes=self.session_period):
            logger.info("The period session has exceeded.")
            self.login()

        try:
            response = self.session.post(
                TLExtenderURLs.HOSTS,
                params=dict(id=self.id),
                headers=TLExtenderLogin.HEADERS,
                data=TLExtenderData.HOSTS,
                timeout=10
            )
            response.raise_for_status()
        except RequestException as e:
            error_msg = f"Failed to get connected devices: {e}, Response: {response.text if 'response' in locals() else 'N/A'}"
            logger.error(error_msg)
            raise APIError(error_msg) from e

        if not response.text:
            raise APIError("Empty response when getting devices")

        try:
            devices_df = TLExtenderUtils.devices_handle(response.text)
        except Exception as e:
            logger.error(f"Failed to parse devices response: {e}")
            raise DataParsingError(f"Failed to parse devices data: {e}") from e

        if not isinstance(devices_df, pd.DataFrame):
            raise DataParsingError(
                f"Unexpected devices response format: {type(devices_df)}"
            )

        logger.info(
            f"Successfully retrieved {len(devices_df)} connected devices")
        return devices_df


def main():
    extender = TLExtender()
    extender.login()
    print(extender.get_connected_devices())


if __name__ == "__main__":
    main()
