from dataclasses import dataclass


@dataclass(frozen=True)
class TLExtenderColumns:
    """
    Schema for TLExtender raw column names.
    """
    IP_ADDRESS: str = "ip"
    MAC_ADDRESS: str = "mac"
    BIND_ENTRY: str = "bindEntry"
    STA_MGT_ENTRY: str = "staMgtEntry"
    TYPE: str = "type"
    ONLINE: str = "online"
    NAME: str = "name"
    DEVICE_TYPE: str = "DevType"
