from wlan.schemas import StandardColumns as S
from wlan.schemas import TLExtenderColumns as T

TLEXTENDER_COLUMNS_MAP = {
    T.MAC_ADDRESS: S.MAC_ADDRESS,
    T.IP_ADDRESS: S.IP_ADDRESS,
    T.NAME: S.HOST_NAME,
    T.ONLINE: S.ACTIVE,
    T.DEVICE_TYPE: S.DEVICE_TYPE,
    T.TYPE: S.HOST_TYPE,
    T.BIND_ENTRY: S.BIND_ENTRY,
    T.STA_MGT_ENTRY: S.STA_MGT_ENTRY,
}
