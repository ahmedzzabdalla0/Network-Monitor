import json
import logging
from typing import Dict, List, Optional, Union

import pandas as pd
from requests import RequestException, Response, Session

from .constants import ZyxelGatewayURLs, ZyxelLoginConstants
from .exceptions import (APIError, AuthenticationError, DataParsingError,
                         SessionError)
from .utils import ZyxelGatewayUtils

# Configure logging
logger = logging.getLogger(__name__)


class ZyxelClient:
    """
    Client for interacting with the Zyxel VMG3625-T50B router's API.
    Handles session management, login, encryption, and data retrieval.
    """

    def __init__(self):
        """Initializes the client session and stores the primary decryption key."""
        self.session = Session()
        self.session.verify = False  # Ignore SSL warnings for local IP
        self.encryption_key: Optional[str] = None
        self.session_key: Optional[str] = None
        logger.info("ZyxelClient initialized")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures logout."""
        if self.session_key:
            try:
                self.logout()
            except Exception as e:
                logger.error(f"Error during context manager cleanup: {e}")

    def login(
        self,
        username: str = ZyxelLoginConstants.USERNAME,
        password: str = ZyxelLoginConstants.PASSWORD
    ) -> bool:
        """
        Performs login with username and password by encrypting credentials.

        Args:
            username: Router username (defaults to constant).
            password: Router password (defaults to constant).

        Returns:
            True on successful login.

        Raises:
            AuthenticationError: If login fails.
            APIError: If API request fails.
        """
        logger.info(f"Attempting login for user: {username}")

        try:
            # Encode password
            encoded_password = ZyxelGatewayUtils.encode_password(password)

            # Prepare content object
            raw_content_obj = ZyxelLoginConstants.RAW_OBJECT.copy()
            raw_content_obj["Input_Account"] = username
            raw_content_obj["Input_Passwd"] = encoded_password

            # Generate encryption keys
            self.encryption_key, iv = ZyxelGatewayUtils.generate_aes_key_iv()

            # Encrypt encryption_key using RSA
            rsa_encrypted_key = ZyxelGatewayUtils.encrypt_rsa(
                ZyxelLoginConstants.RSA_PUBLIC_KEY, self.encryption_key
            )

            # Encrypt login data
            raw_content = ZyxelGatewayUtils.stringify_content(raw_content_obj)
            encrypted_content = ZyxelGatewayUtils.encrypt_aes(
                self.encryption_key, iv, raw_content
            )

            # Prepare payload
            login_payload = ZyxelGatewayUtils.create_post_payload(
                encrypted_content, rsa_encrypted_key, iv
            )

            # Send login request
            response = self.session.post(
                ZyxelGatewayURLs.LOGIN,
                data=login_payload,
                timeout=10
            )
            response.raise_for_status()

        except RequestException as e:
            error_msg = f"(Login) Login request failed: {e}, Respose: {response.text}"
            logger.error(error_msg)
            raise APIError(error_msg) from e

        try:
            login_info = self._decrypt_response(response)
        except (DataParsingError, Exception) as e:
            logger.error(f"Failed to decrypt login response: {e}")
            raise AuthenticationError(
                f"Failed to process login response: {e}") from e

        if not isinstance(login_info, dict):
            raise AuthenticationError(
                f"Unexpected login response format: {type(login_info)}")

        self.session_key = login_info.get("sessionkey")
        if not self.session_key:
            logger.error(f"Login response missing sessionkey: {login_info}")
            raise AuthenticationError(
                "Login response did not contain a valid session key")

        logger.info(f"Login successful. Session Key: {self.session_key}")
        return True

    def login_with_cached_data(self) -> bool:
        """
        Performs the login using the pre-cached (hardcoded) encrypted data.

        Returns:
            True on successful login.

        Raises:
            AuthenticationError: If login fails.
            APIError: If API request fails.
        """
        logger.info("Attempting login using cached credentials...")

        self.encryption_key = ZyxelLoginConstants.KEY
        login_data = ZyxelLoginConstants.FINAL_POST_DATA

        try:
            response = self.session.post(
                ZyxelGatewayURLs.LOGIN,
                data=login_data,
                timeout=10
            )
            response.raise_for_status()
        except RequestException as e:
            error_msg = f"(Cached Login) Login request failed: {e}, Respose: {response.text}"
            logger.error(error_msg)
            raise APIError(error_msg) from e

        try:
            login_info = self._decrypt_response(response)
        except (DataParsingError, Exception) as e:
            logger.error(f"Failed to decrypt login response: {e}")
            raise AuthenticationError(
                f"Failed to process login response: {e}") from e

        if not isinstance(login_info, dict):
            raise AuthenticationError(
                f"Unexpected login response format: {type(login_info)}")

        self.session_key = login_info.get("sessionkey")
        if not self.session_key:
            logger.error(f"Login response missing sessionkey: {login_info}")
            raise AuthenticationError(
                "Login response did not contain a valid session key")

        logger.info(f"Login successful. Session Key: {self.session_key}")
        return True

    def logout(self) -> Dict:
        """
        Logs out the current session using the stored session key.

        Returns:
            Logout response as dict.

        Raises:
            SessionError: If not logged in or logout fails.
        """
        if not self.session_key:
            raise SessionError(
                "Cannot logout: Not logged in or session key is missing")

        logger.info("Logging out...")

        try:
            response = self.session.post(
                ZyxelGatewayURLs.LOGOUT,
                params={"sessionkey": self.session_key},
                timeout=10
            )
            response.raise_for_status()
        except RequestException as e:
            logger.error(f"Logout request failed: {e}")
            raise APIError(f"Logout request failed: {e}") from e

        try:
            logout_data = response.json()
            logger.info("Logout successful")
            self.session_key = None
            return logout_data
        except json.JSONDecodeError as e:
            logger.warning(f"Logout response not JSON: {e}")
            self.session_key = None
            return {"status": "logged_out", "note": "Non-JSON response received"}

    def _decrypt_response(self, response: Response) -> Union[Dict, List, str]:
        """
        Handles the standard Zyxel API response by decrypting the content.

        Args:
            response: HTTP response object.

        Returns:
            Decrypted content as dict or string.

        Raises:
            APIError: If response cannot be processed.
            DataParsingError: If JSON parsing fails.
        """
        try:
            response_json = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Non-JSON response from {response.url}: {e}")
            raise DataParsingError(
                f"Non-JSON response received from {response.url}. "
                f"Status: {response.status_code}, Body: {response.text[:200]}"
            ) from e

        return ZyxelGatewayUtils.parse_api_response(response_json, self.encryption_key)

    def get_all_hosts(
        self,
    ) -> pd.DataFrame:
        """
        Retrieves the list of all hosts and returns a DataFrame (With StandardColumns).

        Returns:
            DataFrame containing all hosts information (With StandardColumns).

        Raises:
            SessionError: If not logged in.
            APIError: If API request fails.
            DataParsingError: If response cannot be parsed.
        """
        if not self.session_key:
            raise SessionError("Cannot retrieve hosts: Not logged in")

        logger.info("Scanning all hosts...")

        try:
            response = self.session.get(ZyxelGatewayURLs.HOSTS, timeout=10)
            response.raise_for_status()
        except RequestException as e:
            logger.error(f"Device scan request failed: {e}")
            raise APIError(f"Device scan request failed: {e}") from e

        devices_data = self._decrypt_response(response)

        if not isinstance(devices_data, dict) or not devices_data.get('Object'):
            logger.error(f"Unexpected devices data structure: {devices_data}")
            raise DataParsingError(
                "Could not retrieve devices list: Invalid response structure")

        try:
            hosts_list: List = devices_data['Object'][0]['lanhosts']
            return ZyxelGatewayUtils.hosts_handle(hosts_list)

        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to parse devices data: {e}")
            raise DataParsingError(f"Failed to parse devices data: {e}") from e

    def get_connected_devices(self) -> pd.DataFrame:
        """
        Retrieves the list of connected devices (ONLY With Wlan) and returns a DataFrame (With StandardColumns).

        Returns:
            DataFrame containing connected devices information (With StandardColumns).

        Raises:
            SessionError: If not logged in.
            APIError: If API request fails.
            DataParsingError: If response cannot be parsed.
        """
        if not self.session_key:
            raise SessionError(
                "Cannot retrieve connected devices: Not logged in")

        logger.info("Scanning connected devices...")

        try:
            response = self.session.get(ZyxelGatewayURLs.WLAN, timeout=10)
            response.raise_for_status()
        except RequestException as e:
            logger.error(f"Device scan request failed: {e}")
            raise APIError(f"Device scan request failed: {e}") from e

        devices_data = self._decrypt_response(response)

        if not isinstance(devices_data, list):
            logger.error(f"Unexpected devices data structure: {devices_data}")
            raise DataParsingError(
                "Could not retrieve devices list: Invalid response structure")

        hosts = self.get_all_hosts()

        return ZyxelGatewayUtils.wlan_handle(devices_data, hosts)


def get_router_df() -> pd.DataFrame:
    """
    Logs in using ZyxelClient, retrieves and processes all router data,
    then returns it as a pandas DataFrame.

    Args:
        None

    Returns:
        pd.DataFrame: The processed router data.

    Performance:
        Takes approximately 1 second to complete.
    """
    with ZyxelClient() as router:
        router.login_with_cached_data()
        return router.get_connected_devices()


def main():
    """Main execution function with proper error handling."""
    try:
        router_df = get_router_df()
        print(router_df)

    except AuthenticationError as e:
        logger.error(f"Authentication failed: {e}")
        print(f"Login Error: {e}")
    except SessionError as e:
        logger.error(f"Session error: {e}")
        print(f"Session Error: {e}")
    except APIError as e:
        logger.error(f"API error: {e}")
        print(f"API Error: {e}")
    except DataParsingError as e:
        logger.error(f"Data parsing error: {e}")
        print(f"Data Error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Unexpected Error: {e}")


if __name__ == '__main__':
    main()
