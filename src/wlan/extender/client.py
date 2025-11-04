
import logging
from time import sleep

import pandas as pd
from requests import Session

from .constants import TLExtenderData, TLExtenderLogin, TLExtenderURLs
from .utils import TLExtenderUtils

logger = logging.getLogger(__name__)


class TLExtender:
    def __init__(self):
        self.session = Session()
        self.id = self.get_token()

    def get_token(self) -> str:
        id = TLExtenderUtils.su_encrypt(TLExtenderLogin.PASSWORD)
        response = self.session.post(
            TLExtenderURLs.GET_TOKEN,
            headers=TLExtenderLogin.HEADERS,
        )
        id = TLExtenderUtils.id_encrypt(response.text, id)

        # Confirm Token
        re = self.session.post(
            TLExtenderURLs.CONFIRM_ID,
            params=dict(id=id),
            headers=TLExtenderLogin.HEADERS
        )
        return id

    def get_connected_devices(self) -> pd.DataFrame:
        response = self.session.post(
            TLExtenderURLs.HOSTS,
            params=dict(id=self.id),
            headers=TLExtenderLogin.HEADERS,
            data=TLExtenderData.HOSTS
        )

        return TLExtenderUtils.devices_handle(response.text)
