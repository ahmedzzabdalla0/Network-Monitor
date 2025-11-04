
import pandas as pd
import wlan.logging_runner
from wlan.extender.client import TLExtender
import logging

from wlan.managers import TimerManager
from wlan.router import get_router_df
from wlan.utils import PathUtils

logger = logging.getLogger(__name__)

BASE_PATH = PathUtils.get_base_path()


def main():
    with TimerManager():
        extender = TLExtender()
        extender_df = extender.get_connected_devices()
    router_pd = get_router_df()
    print(pd.concat([extender_df, router_pd]).fillna("Unknown"))


if __name__ == "__main__":
    main()
