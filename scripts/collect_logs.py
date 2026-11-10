"""
Netmiko: Collect logs from Cisco IOS switches via SSH
"""
import os
from datetime import datetime
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

DEVICES = [
    {
        "name": "SW1",
        "device_type": "cisco_ios",
        "host": "192.168.56.101",
        "username": os.environ.get("NET_USER", "admin"),
        "password": os.environ.get("NET_PASS", "admin"),
    },
    {
        "name": "SW2",
        "device_type": "cisco_ios",
        "host": "192.168.56.102",
        "username": os.environ.get("NET_USER", "admin"),
        "password": os.environ.get("NET_PASS", "admin"),
    },
]

COMMANDS = [
    "show logging",
    "show interfaces status",
    "show cpu",
    "show memory statistics",
]

def collect_from_device(device):
    output_dir = "data/logs"
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{output_dir}/{device['name']}_{timestamp}.txt"
    results = {}
    try:
        with ConnectHandler(**device) as conn:
            for cmd in COMMANDS:
                output = conn.send_command(cmd, read_timeout=30)
                results[cmd] = output
    except Exception as e:
        print(f"  [ERROR] {device['name']}: {e}")
        return None
    with open(filepath, "w") as f:
        f.write(f"Device: {device['name']}\n")
        f.write(f"Collected: {timestamp}\n")
        f.write("=" * 60 + "\n\n")
        for cmd, output in results.items():
            f.write(f"===== {cmd} =====\n{output}\n\n")
    print(f"  [OK] {device['name']} -> {filepath}")
    return filepath

def main():
    print("=" * 60)
    print(f"NETOPS LOG COLLECTION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Devices: {len(DEVICES)}")
    print("=" * 60)
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(collect_from_device, d): d['name'] for d in DEVICES}
        for future in as_completed(futures):
            result = future.result()
            if result:
                print(f"  Saved: {result}")
    print("\n[OK] Collection complete.")

if __name__ == "__main__":
    main()   
