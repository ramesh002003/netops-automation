"""
Detection Engine: L2/L3 Loop, MAC Flapping, DNS, Routing Issues
"""
import os
import re
import json
from pathlib import Path

LOG_DIR = "data/logs"
OUTPUT_DIR = "data/parsed"

def detect_l2_loop(text):
    issues = []
    patterns = {
        "STP Topology Change": r"(topology change|TCN|BPDU.*received)",
        "L2 Loop Detected": r"(L2.*loop|loop.*detected|port.*disabled.*reason.*loop)",
        "Port Flapping": r"(port.*up.*down.*up|link.*flap|LINEPROTO.*UPDOWN)",
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "L2_LOOP",
                "severity": "CRITICAL",
                "title": name,
                "evidence": matches[:10],
                "count": len(matches),
            })
    return issues

def detect_l3_loop(text):
    issues = []
    patterns = {
        "TTL Expired": r"(TTL.*expired|time to live.*exceeded)",
        "IP Forwarding Error": r"(IP.*forwarding.*error|packet.*dropped.*TTL)",
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "L3_LOOP",
                "severity": "CRITICAL",
                "title": name,
                "evidence": matches[:10],
                "count": len(matches),
            })
    return issues

def detect_mac_flapping(text):
    issues = []
    mac_port_pattern = r"([0-9a-f]{4}\.[0-9a-f]{4}\.[0-9a-f]{4}).*?(Gi[0-9/]+|Fa[0-9/]+|Te[0-9/]+)"
    mac_ports = {}
    for line in text.splitlines():
        for match in re.finditer(mac_port_pattern, line, re.IGNORECASE):
            mac = match.group(1).lower()
            port = match.group(2)
            mac_ports.setdefault(mac, set()).add(port)
    for mac, ports in mac_ports.items():
        if len(ports) > 1:
            issues.append({
                "type": "MAC_FLAPPING",
                "severity": "HIGH",
                "title": f"MAC {mac} on {len(ports)} ports",
                "evidence": [f"MAC: {mac} -> Ports: {', '.join(sorted(ports))}"],
                "count": len(ports),
            })
    flap_pattern = r"(MAC.*flap|FLAPPING|address.*move.*detect)"
    flap_matches = re.findall(flap_pattern, text, re.IGNORECASE)
    if flap_matches:
        issues.append({
            "type": "MAC_FLAPPING",
            "severity": "HIGH",
            "title": "MAC Flapping in logs",
            "evidence": flap_matches[:10],
            "count": len(flap_matches),
        })
    return issues

def detect_dns_issues(text):
    issues = []
    patterns = {
        "DNS Timeout": r"(DNS.*timeout|NXDOMAIN|name.*resolution.*failed)",
        "DNS Unreachable": r"(DNS.*unreachable|no response.*DNS|DNS.*server.*unreachable)",
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            issues.append({
                "type": "DNS_ISSUE",
                "severity": "MEDIUM",
                "title": name,
                "evidence": matches[:10],
                "count": len(matches),
            })
    return issues

def detect_routing_issues(text):
    issues = []
    patterns = {
        "OSPF Neighbor Down": r"(OSPF.*adjacency.*DOWN|OSPF.*neighbor.*down|ADJCHG)",
        "BGP Peer Down": r"(BGP.*session.*closed|BGP.*peer.*down|keepalive.*timeout)",
        "Interface Down": r"(LINEPROTO.*changed state to down|interface.*down.*line.*protocol)",
    }
    for name, pat in patterns.items():
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            sev = "HIGH" if name in ("OSPF Neighbor Down", "BGP Peer Down") else "MEDIUM"
            issues.append({
                "type": "ROUTING_ISSUE",
                "severity": sev,
                "title": name,
                "evidence": matches[:10],
                "count": len(matches),
            })
    return issues

def parse_interface_status(text):
    interfaces = []
    for line in text.splitlines():
        if line.startswith(("Port", "----")):
            continue
        parts = line.split()
        if len(parts) >= 5:
            interfaces.append({
                "port": parts[0], "name": parts[1], "status": parts[2],
                "vlan": parts[3], "duplex": parts[4],
                "speed": parts[5] if len(parts) > 5 else "",
            })
    return interfaces

def parse_cpu_memory(text):
    cpu_match = re.search(r"CPU utilization.*?:\s*([\d.]+)%", text)
    mem_match = re.search(r"Memory:\s*([\d.]+)%", text)
    return {
        "cpu_percent": float(cpu_match.group(1)) if cpu_match else None,
        "memory_percent": float(mem_match.group(1)) if mem_match else None,
    }

def parse_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    count = 0
    for log_file in Path(LOG_DIR).glob("*.txt"):
        content = log_file.read_text()
        all_issues = []
        all_issues += detect_l2_loop(content)
        all_issues += detect_l3_loop(content)
        all_issues += detect_mac_flapping(content)
        all_issues += detect_dns_issues(content)
        all_issues += detect_routing_issues(content)
        parsed = {
            "device": log_file.stem.split("_")[0],
            "timestamp": log_file.stem.split("_")[1] if "_" in log_file.stem else "",
            "interfaces": parse_interface_status(content),
            "cpu_memory": parse_cpu_memory(content),
            "issues": all_issues,
            "issue_count": len(all_issues),
            "raw_size_bytes": len(content),
        }
        out_path = os.path.join(OUTPUT_DIR, log_file.stem + ".json")
        with open(out_path, "w") as f:
            json.dump(parsed, f, indent=2)
        status = "ALERTS" if all_issues else "CLEAR"
        print(f"  [{status}] {log_file.name} -> {len(all_issues)} issues")
        for issue in all_issues:
            print(f"    [{issue['severity']}] {issue['type']}: {issue['title']}")
        count += 1
    print(f"\n[OK] {count} files parsed -> {OUTPUT_DIR}/")

if __name__ == "__main__":
    print("=" * 60)
    print("NETOPS DETECTION ENGINE")
    print("=" * 60)
    parse_all()   
