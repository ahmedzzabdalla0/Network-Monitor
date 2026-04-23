
import wlan.logging_runner
import os
import logging
from datetime import datetime
from threading import RLock
from time import sleep

import pandas as pd

from wlan.extender.client import TLExtender
from wlan.managers.config_manager import ConfigManager
from wlan.observers import DeviceChangeNotifier
from wlan.router.client import ZyxelClient
from wlan.notifiers import TelegramNotifier, WindowsNotifier
from wlan.utils import DataframeUtils, PathUtils, ThreadUtils

logger = logging.getLogger(__name__)

BASE_PATH = PathUtils.get_base_path()


class MonitorState:
    def __init__(self):
        self.running = True
        self.wait_time = int(ConfigManager.get("main.wait_time", 3))
        self.last_devices = pd.DataFrame()
        self.last_fetch_at = None
        self.last_error = None
        self.lock = RLock()


def main():
    # Initialize Config Variables
    state = MonitorState()

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
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                return extender.get_connected_devices()
            except Exception as e:
                logger.error(
                    "Extender fetch failed (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    e
                )
                try:
                    extender.login()
                except Exception as login_error:
                    logger.error("Extender relogin failed: %s", login_error)
        logger.error("Extender unavailable after retries; using empty dataset.")
        return pd.DataFrame()

    def get_router_devices():
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                return router.get_connected_devices()
            except Exception as e:
                logger.error(
                    "Router fetch failed (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    e
                )
                try:
                    router.login_with_cached_data()
                except Exception as login_error:
                    logger.error("Router relogin failed: %s", login_error)
        logger.error("Router unavailable after retries; using empty dataset.")
        return pd.DataFrame()

    # Getter the final db
    def get_devices():
        with state.lock:
            extender_df, router_df = ThreadUtils.fire_and_wait(
                get_extender_devices,
                get_router_devices
            )
            devices = DataframeUtils.finalize_dfs(extender_df, router_df)
            state.last_devices = devices.copy()
            state.last_fetch_at = datetime.now()
            return devices

    def get_status_message():
        status = "RUNNING" if state.running else "STOPPED"
        wait_time = state.wait_time
        device_count = len(state.last_devices) if isinstance(state.last_devices, pd.DataFrame) else 0
        last_fetch = state.last_fetch_at.strftime("%Y-%m-%d %H:%M:%S") if state.last_fetch_at else "N/A"
        error = type(state.last_error).__name__ if state.last_error else "None"
        return (
            "ℹ️ <b>Monitor Status</b>\n"
            f"<b>State:</b> {status}\n"
            f"<b>Wait Time:</b> {wait_time}s\n"
            f"<b>Last Devices Count:</b> {device_count}\n"
            f"<b>Last Fetch:</b> {last_fetch}\n"
            f"<b>Last Error:</b> {error}"
        )

    def stop_monitor():
        state.running = False
        return "⏸ Monitoring paused successfully."

    def start_monitor():
        state.running = True
        state.last_error = None
        return "▶️ Monitoring resumed."

    def retry_monitor():
        with state.lock:
            try:
                extender.login()
                router.login_with_cached_data()
                state.running = True
                state.last_error = None
                return "🔁 Retry successful. Monitoring resumed."
            except Exception as e:
                state.last_error = e
                logger.error("Retry failed: %s", e, exc_info=True)
                return f"❌ Retry failed: <code>{e}</code>"

    def reload_config():
        with state.lock:
            try:
                ConfigManager.reload_config()
                state.wait_time = int(ConfigManager.get("main.wait_time", 3))
                notifier.reset()
                return "🔄 config.yaml reloaded and notifier cache reset."
            except Exception as e:
                state.last_error = e
                logger.error("Reload config failed: %s", e, exc_info=True)
                return f"❌ Reload failed: <code>{e}</code>"

    def upsert_host(mac: str, name: str, device_type: str):
        try:
            if not name:
                return "❌ Host name is required."
            if not device_type:
                return "❌ Device type is required."

            payload = {
                "Name": name.strip(),
                "Device Type": device_type.strip().upper()
            }
            result = ConfigManager.upsert_cached_host(mac, payload)
            notifier.reset()
            return (
                "✅ Host saved successfully.\n"
                f"MAC: <code>{mac.strip().lower()}</code>\n"
                f"Name: {result.get('Name', 'Unknown')}\n"
                f"Type: {result.get('Device Type', 'Unknown')}"
            )
        except Exception as e:
            logger.error("Host upsert failed: %s", e, exc_info=True)
            return f"❌ Failed to save host: <code>{e}</code>"

    def delete_host(mac: str):
        try:
            removed = ConfigManager.delete_cached_host(mac)
            if not removed:
                return f"⚠️ MAC not found: <code>{mac.strip().lower()}</code>"
            notifier.reset()
            return f"🗑 Host removed successfully: <code>{mac.strip().lower()}</code>"
        except Exception as e:
            logger.error("Host delete failed: %s", e, exc_info=True)
            return f"❌ Failed to delete host: <code>{e}</code>"

    telegram.register_control_handlers(
        get_devices=get_devices,
        start_monitor=start_monitor,
        stop_monitor=stop_monitor,
        retry_monitor=retry_monitor,
        reload_config=reload_config,
        upsert_host=upsert_host,
        delete_host=delete_host,
        get_status=get_status_message
    )
    telegram.start_control_bot()
    telegram.send_text("🤖 Telegram menu is ready. Send /menu to open commands.")

    try:
        while True:
            if not state.running:
                sleep(1)
                continue

            try:
                devices = get_devices()
                notifier.process(devices)
                os.system("cls")
                print(devices)
                print(f"[+] Waiting {state.wait_time} second/s ...", flush=True)
                sleep(state.wait_time)
                print("[+] Fetching ...", flush=True)
            except Exception as e:
                state.last_error = e
                state.running = False
                logger.error("Monitor loop crashed: %s", e, exc_info=True)
                telegram.send_runtime_error(e)
                sleep(2)
    finally:
        router.logout()


if __name__ == "__main__":
    main()
