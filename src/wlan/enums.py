from enum import Enum


class ConnectionStatus(Enum):
    """Device connection status"""
    CONNECTED = 1
    DISCONNECTED = 2


class DeviceType(Enum):
    """Type of network device"""
    COMPUTER = "Computer"
    PHONE = "Phone"
    TABLET = "Tablet"
    LAPTOP = "Laptop"
    MACHINE = "Machine"
    OTHER = "Other"


class DeviceSource(Enum):
    """Source of device discovery"""
    EXTENDER = "extender"
    NMAP = "nmap"
