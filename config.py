from enums import DeviceType


EXT_IP = "192.168.1.207"
NETWORK_RANGE = "192.168.1.0/24"
NMAP_ARGS = "-sS -p 80"
EXCLUDE_IPS = ["192.168.1.207", "192.168.1.1", "192.168.1.32"]
EXCLUDE_MACS = ["b2:19:21:09:96:75"]
NMAP_PATH = "C:\\Program Files (x86)\\Nmap\\nmap.exe"
CACHED_HOSTNAMES = {
    'ac:49:db:52:bd:f2': {'name': 'Asmaa', 'DevType': DeviceType.PHONE},
    '94:16:25:8c:45:4c': {'name': 'Mostafa', 'DevType': DeviceType.PHONE},
    'c0:3d:03:26:2f:81': {'name': 'Mam', 'DevType': DeviceType.PHONE},
    '28:2d:7f:9f:54:05': {'name': 'My Iphone', 'DevType': DeviceType.PHONE},
    'd4:50:ee:57:1a:d6': {'name': 'Washing machine', 'DevType': DeviceType.MACHINE},
    '7c:d2:da:b9:47:63': {'name': 'Dad', 'DevType': DeviceType.PHONE},
}
SHOWED_COLUMNS = ["name", "ip", "mac", "source", "DevType"]
