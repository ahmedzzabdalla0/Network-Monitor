
import wlan.logging
import logging

from wlan.managers import TimerManager
from wlan.router import get_router_df
from wlan.utils import PathUtils

logger = logging.getLogger(__name__)

BASE_PATH = PathUtils.get_base_path()


def main():
    with TimerManager():
        router_pd = get_router_df()
    print(router_pd)


if __name__ == "__main__":
    main()
