
import wlan.logging_runner
import os
import logging
from time import sleep

from wlan.extender.client import TLExtender
from wlan.managers.config_manager import ConfigManager
from wlan.observers import DeviceChangeNotifier
from wlan.router.client import ZyxelClient
from wlan.notifiers import TelegramNotifier, WindowsNotifier
from wlan.utils import DataframeUtils, PathUtils, ThreadUtils

logger = logging.getLogger(__name__)

BASE_PATH = PathUtils.get_base_path()


def main():
    # Initialize Config Variables
    wait_time = int(ConfigManager.get("main.wait_time", 3))

    # Initialize Notifiers
    telegram = TelegramNotifier()
    windows = WindowsNotifier()

    # Use with DeviceChangeNotifier
    notifier = DeviceChangeNotifier(
        [
            telegram.send_notification,
            windows.send_notification
        ]
    )

    # Initialize Network Clients
    extender = TLExtender()
    extender.login()

    router = ZyxelClient()
    router.login_with_cached_data()

    # Adabt with exceptions
    def get_extender_devices():
        try:
            return extender.get_connected_devices()
        except Exception as e:
            logger.error(f"Extender Fails: Trying to relogin, Error: {e}")
            extender.login()
            return get_extender_devices()

    def get_router_devices():
        try:
            return router.get_connected_devices()
        except Exception as e:
            logger.error(f"Router Fails: Trying to relogin, Error: {e}")
            router.login_with_cached_data()
            return get_router_devices()

    # Getter the final db
    def get_devices():
        extender_df, router_df = ThreadUtils.fire_and_wait(
            get_extender_devices,
            get_router_devices
        )
        return DataframeUtils.finalize_dfs(extender_df, router_df)

    try:
        while True:
            devices = get_devices()
            notifier.process(devices)
            os.system("cls")
            print(devices)
            print(f"[+] Waiting {wait_time} second/s ...", flush=True)
            sleep(wait_time)
            print("[+] Fetching ...", flush=True)
    finally:
        router.logout()


if __name__ == "__main__":
    main()
