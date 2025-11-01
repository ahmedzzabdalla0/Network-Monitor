import os
import time
import requests
import pandas as pd
import nmap
from urllib.parse import quote
from tabulate import tabulate
from plyer import notification
from dotenv import load_dotenv
import config
from enums import ConnectionStatus, DeviceType, DeviceSource
from telegramy import Bot

load_dotenv(override=True)

# Settings from config and env
PASSWORD = os.getenv('EXTENDER_PASSWORD')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')


class Extender:
    def __init__(self, ip: str, password: str):
        self.s = requests.Session()
        self.ip = ip
        self.headers = {"Referer": f"http://{self.ip}/"}
        self.password = password
        self.token = self.get_token()
        self.bot = Bot(token=BOT_TOKEN)
        self.cache = config.CACHED_HOSTNAMES
        self.current = pd.DataFrame()
        self.first_run = True
        self.nm = nmap.PortScanner([config.NMAP_PATH])

    @staticmethod
    def su_encrypt(e: str, t: str = None, r: str = None) -> str:
        if r is None:
            r = "yLwVl0zKqws7LgKPRQ84Mdt708T1qQ3Ha7xv3H7NyU84p21BriUWBU43odz3iP4rBL3cD02KZciXTysVXiV8ngg6vL48rPJyAUw0HurW20xqxv9aYb4M9wK1Ae0wlro510qXeU07kV57fQMc8L6aLgMLwygtc0F10a0Dg70TOoouyFhdysuRMO51yY5ZlOZZLEal1h0t9YQW0Ko7oBwmCAHoic4HYbUyVeU3sfQ1xtXcPcf1aT303wAQhv66qzW"
        if t is None:
            t = "RDpbLfCPsJZ7fiv"
        n = []
        o, l, u = len(e), len(t), len(r)
        d = max(o, l)
        for h in range(d):
            s = 187 if o <= h else ord(e[h])
            a = 187 if l <= h else ord(t[h])
            n.append(r[(s ^ a) % u])
        return ''.join(n)

    def get_token(self) -> str:
        init_id = self.su_encrypt(self.password)
        rsa = self.s.post(
            f"http://{self.ip}/?code=7&asyn=1",
            headers=self.headers,
        )
        auth3, auth4 = rsa.text.splitlines()[3:5]
        token = quote(self.su_encrypt(auth3, init_id, auth4), safe='')
        self.s.post(
            f"http://{self.ip}/?code=7&asyn=0&id={token}",
            headers=self.headers
        )
        return token

    def _get_extender_clients(self, exclude_ips: list[str], exclude_macs: list[str]) -> pd.DataFrame:
        print("Scan Extender...")
        text_response = self.s.post(
            f"http://{self.ip}/?code=2&asyn=0&id={self.token}",
            headers=self.headers,
            data="13|1,0,0"
        ).text

        data = {}
        for line in text_response.strip().splitlines():
            parts = line.strip().split(" ", 2)
            if len(parts) == 3:
                key, idx, val = parts
                data.setdefault(key, {})[idx] = val

        rows = [{k: (data[k].get(i) if isinstance(data[k], dict) else data[k])
                for k in data} for i in data.get("ip", {}).keys()]

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df["mac"] = df["mac"].str.lower().str.replace("-", ":")
        df = df[
            df["ip"].notna()
            & (df["ip"] != "0.0.0.0")
            & ~df["ip"].isin(exclude_ips)
        ]
        df = df[
            df["mac"].notna()
            & (df["mac"] != "00:00:00:00:00:00")
            & ~df["mac"].isin(exclude_macs)
        ]
        df['source'] = DeviceSource.EXTENDER.value

        return df

    def _nmap(self, exclude_ips: list[str], exclude_macs: list[str]) -> pd.DataFrame:
        print("Scan Nmap...")
        try:
            self.nm.scan(
                hosts=config.NETWORK_RANGE,
                arguments=config.NMAP_ARGS
            )
            clients = []
            for host in self.nm.all_hosts():
                if host in exclude_ips or self.nm[host].state() != 'up':
                    continue

                mac = self.nm[host]['addresses'].get(
                    'mac', 'N/A').lower() if 'addresses' in self.nm[host] else 'N/A'
                if mac in exclude_macs:
                    continue

                vendor = list(self.nm[host]['vendor'].values())[
                    0] if 'vendor' in self.nm[host] and self.nm[host]['vendor'] else "Unknown"
                hostname = self.nm[host].hostname() or "Unknown"

                clients.append({
                    'ip': host,
                    'mac': mac,
                    'name': hostname,
                    'DevType': vendor,
                    'source': DeviceSource.NMAP.value
                })

            return pd.DataFrame(clients)
        except Exception as e:
            print(f"[!] Nmap error: {e}")
            return pd.DataFrame()

    def verify_nmap(self, ip: str) -> bool:
        try:
            self.nm.scan(
                hosts=ip,
                arguments=config.NMAP_ARGS
            )
            return ip in self.nm.all_hosts() and self.nm[ip].state() == 'up'
        except:
            return False

    def get_all_clients(self) -> pd.DataFrame:
        ext_df = self._get_extender_clients(
            config.EXCLUDE_IPS,
            config.EXCLUDE_MACS
        )
        exclude_ips = config.EXCLUDE_IPS
        if not ext_df.empty:
            exclude_ips = [*{*(config.EXCLUDE_IPS + ext_df['ip'].tolist())}]
        nmap_df = self._nmap(
            exclude_ips,
            config.EXCLUDE_MACS
        )
        df_array = []
        df = pd.DataFrame()
        if not ext_df.empty:
            df_array.append(ext_df)
        if not nmap_df.empty:
            df_array.append(nmap_df)
        if len(df_array):
            df = pd.concat(df_array,
                           ignore_index=True
                           ).drop_duplicates(subset=['ip'])

        if df.empty:
            if not self.current.empty:
                verified = [d for _, d in self.current.iterrows()
                            if d['source'] == DeviceSource.EXTENDER.value or not self.verify_nmap(d['ip'])]
                if verified:
                    self.notify(ConnectionStatus.DISCONNECTED,
                                pd.DataFrame(verified))
                    self.current = self.current[~self.current['ip'].isin(
                        [d['ip'] for d in verified])]
            return df

        # Apply cache
        for idx, row in df.iterrows():
            mac = row.get('mac', 'N/A')
            if mac != 'N/A' and mac in self.cache:
                cached = self.cache[mac]
                df.at[idx, 'name'] = cached.get(
                    'name', row.get('name', 'Unknown'))
                df.at[idx, 'DevType'] = cached['DevType'].value if isinstance(
                    cached.get('DevType'), DeviceType) else cached.get('DevType')
            elif mac != 'N/A' and row.get('name', 'Unknown') not in ['Unknown', 'N/A']:
                self.cache[mac] = {'name': row.get('name'), 'DevType': row.get(
                    'DevType', DeviceType.OTHER.value)}

        # Detect changes
        if self.current.empty:
            if self.first_run:
                self.notify_initial(df)
                self.first_run = False
            self.current = df.copy()
            return df

        new = df[~df['ip'].isin(self.current['ip'])]
        deleted_ips = [ip for ip in self.current['ip']
                       if ip not in df['ip'].values]

        if not new.empty:
            self.notify(ConnectionStatus.CONNECTED, new)

        if deleted_ips:
            verified = []
            for ip in deleted_ips:
                dev = self.current[self.current['ip'] == ip].iloc[0]
                if dev['source'] == DeviceSource.EXTENDER.value or not self.verify_nmap(ip):
                    verified.append(ip)
                else:
                    df = pd.concat(
                        [df, self.current[self.current['ip'] == ip]], ignore_index=True)

            if verified:
                self.notify(ConnectionStatus.DISCONNECTED,
                            self.current[self.current['ip'].isin(verified)])

        self.current = df.copy()
        return df

    def notify_initial(self, devices: pd.DataFrame):
        msg = [f"*🔍 Initial Scan*\n",
               f"📊 *Devices:* `{len(devices)}`\n", "─" * 30 + "\n"]
        for _, dev in devices.iterrows():
            emoji = "📱" if "Phone" in str(dev.get('DevType')) else "💻"
            msg.append(
                f"{emoji} *{dev.get('name', 'Unknown')}*\n   └ IP: `{dev.get('ip')}`\n   └ MAC: `{dev.get('mac')}`\n   └ Source: `{dev.get('source').capitalize()}`\n")

        self.bot.send_message(
            chat_id=CHAT_ID,
            text="\n".join(msg).replace("-", "\\-"),
            parse_mode='MarkdownV2'
        )

    def notify(self, status: ConnectionStatus, devices: pd.DataFrame):
        for i, (_, dev) in enumerate(devices.iterrows()):
            name = dev.get('name', 'Unknown')
            title = f'"{name}" {status.name.capitalize()}'

            try:
                notification.notify(
                    app_name="Extender",
                    title=title,
                    message=f"IP: {dev.get('ip')}\nMAC: {dev.get('mac')}\nSource: {dev.get('source')}",
                    timeout=10
                )
            except:
                ...

            msg = f"*{title}*\n\n`IP: {dev.get('ip')}`\n`MAC: {dev.get('mac')}\nSource: {dev.get('source')}`"
            if i != 0:
                time.sleep(2)
            self.bot.send_message(
                chat_id=CHAT_ID,
                text=msg.replace("-", "\\-"),
                parse_mode='MarkdownV2'
            )

    @staticmethod
    def print_clients(df: pd.DataFrame):
        os.system('cls' if os.name == 'nt' else 'clear')
        printed = df[config.SHOWED_COLUMNS].copy()
        printed["DevType"] = printed["DevType"].str.capitalize()
        print(tabulate(printed, headers='keys', tablefmt='psql')
              if not df.empty else "[+] No clients")


def main():
    ext = Extender(config.EXT_IP, PASSWORD)
    print("[+] Ready. Monitoring network...")

    while True:
        try:
            clients = ext.get_all_clients()
            ext.print_clients(clients)
            # print("Waiting 2 Seconeds...")
            # time.sleep(2)
        except requests.exceptions.ConnectionError:
            print("[!] Connection failed. Retrying...")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Error: {e}")
            if "token" in str(e).lower():
                ext.token = ext.get_token()
            time.sleep(5)


if __name__ == "__main__":
    main()
