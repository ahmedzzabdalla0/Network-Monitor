import logging

import pandas as pd
from winotify import Notification, audio

from wlan.constants import AppConstants
from wlan.enums import DeviceChangeEvent
from wlan.exceptions import APIError
from wlan.managers.config_manager import ConfigManager
from wlan.schemas import StandardColumns as S

logger = logging.getLogger(__name__)


class WindowsNotifier:
    """Send device change notifications via Windows notifications.

    This class integrates with DeviceChangeNotifier to send native
    Windows toast notifications when devices connect or disconnect.
    """

    def __init__(self):
        """Initialize Windows notifier.

        Args:
            app_id: Application ID shown in notification (default: "WLAN Monitor")
        """
        self.app_id = AppConstants.APP_ID
        logger.info(
            f"WindowsNotifier initialized with app_id: {AppConstants.APP_ID}")

    def _format_device_summary(self, df: pd.DataFrame) -> str:
        """Format device information as a brief summary.

        Args:
            df: DataFrame containing device information

        Returns:
            str: Brief summary of devices (limited for notification display)
        """
        lines = []
        max_devices = 3

        for idx, (_, device) in enumerate(df.head(max_devices).iterrows(), 1):
            device_info = []
            default_columns = [S.HOST_NAME, S.SOURCE]
            columns = ConfigManager.get("windows_notify.columns")

            if not isinstance(columns, list) or not len(columns):
                logger.warning("Parsing Warning: can't read columns as well")
                columns = default_columns

            for column in columns:
                if column in df.columns and pd.notna(device[column]):
                    device_info.append(device[column])

            lines.append(': '.join(device_info[:2]))

        if len(df) > max_devices:
            lines.append(f"... and {len(df) - max_devices} more")

        return "\n".join(lines)

    def _get_notification_config(self, event: DeviceChangeEvent, device_count: int) -> dict:
        """Get notification configuration based on event type.

        Args:
            event: Type of device change event
            device_count: Number of devices in the event

        Returns:
            dict: Configuration with title, icon, and audio
        """
        device_word = "device" if device_count == 1 else "devices"

        config = {
            DeviceChangeEvent.CONNECTED: {
                "title": f"✅ {device_count} {device_word} connected",
                "icon": AppConstants.ICON_PATH,
                "audio": audio.Default
            },
            DeviceChangeEvent.DISCONNECTED: {
                "title": f"❌ {device_count} {device_word} disconnected",
                "icon": AppConstants.ICON_PATH,
                "audio": audio.Default
            }
        }

        return config.get(event, {
            "title": f"ℹ️ Device update: {device_count} {device_word}",
            "icon": AppConstants.ICON_PATH,
            "audio": audio.Default
        })

    def send_notification(self, df: pd.DataFrame, event: DeviceChangeEvent) -> None:
        """Send device change notification via Windows notification.

        This method is designed to be used as a callback for DeviceChangeNotifier.
        Note: START events are ignored as they're not relevant for notifications.

        Args:
            df: DataFrame containing device information
            event: Type of device change event

        Raises:
            APIError: If notification sending fails
        """
        # Skip START events
        if event == DeviceChangeEvent.START:
            logger.debug("Skipping Windows notification for START event")
            return

        if df.empty:
            logger.warning(
                f"Skipping Windows notification for empty DataFrame (event: {event.value})")
            return

        try:
            device_count = len(df)
            config = self._get_notification_config(event, device_count)

            # Create notification
            toast = Notification(
                app_id=self.app_id,
                title=config["title"],
                msg=self._format_device_summary(df),
                icon=config.get("icon")
            )

            # Set audio
            toast.set_audio(config["audio"], loop=False)

            # Show notification
            toast.show()

            logger.info(
                f"Windows notification sent successfully: {event.value}, {device_count} device(s)")

        except Exception as e:
            logger.error(f"Failed to send Windows notification: {e}")
            raise APIError(f"Failed to send Windows notification: {e}") from e

    def test_notification(self) -> bool:
        """Test Windows notification by sending a test message.

        Returns:
            bool: True if notification is sent successfully

        Raises:
            APIError: If test notification fails
        """
        try:
            toast = Notification(
                app_id=self.app_id,
                title="🔔 WLAN Monitor Test",
                msg="Windows notification is working correctly!",
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()

            logger.info("Windows notification test successful")
            return True

        except Exception as e:
            logger.error(f"Windows notification test failed: {e}")
            raise APIError(f"Windows notification test failed: {e}") from e
