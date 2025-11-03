
from dataclasses import dataclass


@dataclass(frozen=True)
class StandardColumns:
    """
    The single, unified, and standardized set of column names
    for all network device data. This is the "single source of truth".
    """

    # === Unified from both HostColumns & WlanColumns ===
    MAC_ADDRESS: str = "MAC"
    RSSI: str = "RSSI"
    SNR: str = "SNR"
    RATE_KBPS: str = "Rate_kbps"
    SIGNAL_LEVEL: str = "Signal Level"
    SIGNAL_STRENGTH: str = "Signal_Strength"

    # === From HostColumns (with cleaned names) ===
    # --- BASIC IDENTIFICATION ---
    HOST_NAME: str = "Name"
    CURRENT_HOST_NAME: str = "curHostName"
    DEVICE_NAME: str = "Device Name"
    DEVICE_TYPE: str = "Device Type"
    ALIAS: str = "Alias"
    DEVICE_ICON: str = "DeviceIcon"
    ICON: str = "Icon"

    # --- NETWORK ADDRESSING ---
    IP_ADDRESS: str = "IP"
    IP_ADDRESS_V6: str = "IP_Address_v6"
    IP_LINK_LOCAL_V6: str = "IP_Link_Local_v6"
    ADDRESS_SOURCE: str = "Address_Source"
    STATIC_IP: str = "Static_IP"

    # --- DHCP INFORMATION ---
    DHCP_CLIENT: str = "DHCP_Client"
    LEASE_TIME_REMAINING: str = "Lease_Time_Remaining"
    EXPIRE_TIME: str = "Expire_Time"
    CLIENT_ID: str = "Client_ID"
    CLIENT_DUID: str = "Client_DUID"
    VENDOR_CLASS_ID: str = "Vendor_Class_ID"
    USER_CLASS_ID: str = "User_Class_ID"

    # --- CONNECTION DETAILS ---
    ACTIVE: str = "Active"
    ASSOCIATED_DEVICE: str = "Associated_Device"
    LAYER_1_INTERFACE: str = "Layer_1_Interface"
    LAYER_3_INTERFACE: str = "Layer_3_Interface"

    # --- ZYXEL-SPECIFIC BASIC ---
    CONNECTION_TYPE: str = "Connection_Type"
    CONNECTED_AP: str = "Connected_AP"
    HOST_TYPE: str = "Host_Type"
    CAPABILITY_TYPE: str = "Capability_Type"
    LAST_UPDATE: str = "Last_Update"
    SOFTWARE_VERSION: str = "Software_Version"
    DELETE_LEASE: str = "Delete_Lease"

    # --- WIFI-SPECIFIC ---
    WIFI_STATUS: str = "WiFi_Status"
    WIFI_NAME: str = "WiFi_Name"
    SUPPORTED_FREQUENCY_BANDS: str = "Supported_Frequency_Bands"
    SOURCE: str = "Source"

    # --- IPv4/IPv6 COUNTS ---
    IPV4_ADDRESS_COUNT: str = "IPv4_Address_Count"
    IPV6_ADDRESS_COUNT: str = "IPv6_Address_Count"
    ADDRESS_V6_SOURCE: str = "Address_v6_Source"
    DHCP6_CLIENT: str = "DHCP6_Client"

    # --- DHCP POOL & STATIC IP MANAGEMENT ---
    DHCP4_POOL_EXIST: str = "DHCP4_Pool_Exist"
    DHCP4_POOL_IID: str = "DHCP4_Pool_IID"
    DHCP4_STATIC_ADDR_EXIST: str = "DHCP4_Static_Addr_Exist"
    DHCP4_STATIC_ADDR_IID: str = "DHCP4_Static_Addr_IID"
    DHCP4_STATIC_ADDR_ENABLE: str = "DHCP4_Static_Addr_Enable"
    DHCP4_STATIC_ADDR: str = "DHCP4_Static_Addr"
    DHCP4_STATIC_ADDR_NUM: str = "DHCP4_Static_Addr_Num"
    DHCP4_STATIC_ADDR_USED_BY_OTHER: str = "DHCP4_Static_Addr_Used_By_Other"

    # --- PARENTAL CONTROLS ---
    INTERNET_BLOCKING_ENABLED: str = "Internet_Blocking_Enabled"
