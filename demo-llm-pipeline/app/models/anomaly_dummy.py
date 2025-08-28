import itertools, random
from dataclasses import dataclass
from typing import List, Dict
from pandas import DataFrame
from app.utils.tracing import log
from app.utils.tracing import log_gui

@dataclass
class Anomaly:
    id: str
    severity: str
    description: str
    flows: List[Dict]

class AnomalyDetectorMock:
    _cid = itertools.count(1)
    def detect(self, df : DataFrame):
        if random.random() < 0.1:
            log_gui("AnomalyModel", "no anomaly detected")
            return []
        idx = next(self._cid)
        log_gui("AnomalyModel", "anomaly detected")
        return [Anomaly(
            id=f"A-{idx:04d}",
            severity=random.choice(["low", "medium", "high"]),
            description=random.choice([
            "Threshold of bytes per second exceeded",
            "Suspicious DNS burst to 8.8.8.8",
            "Abnormal port scanning activity",
            "High number of failed TCP handshakes (SYN retransmissions)",
            "Unusual outbound traffic volume to a single external IP",
            "Frequent connections to known malicious IP ranges",
            "Excessive DNS NXDOMAIN responses indicating possible DGA",
            "Multiple authentication failures from same source IP",
            "Lateral movement pattern detected across internal subnets",
            "Data exfiltration suspected: large uploads outside business hours",
            "Beaconing behavior: periodic small connections to same C2 endpoint",
            "TLS connections with self-signed or expired certificates",
            "SSH brute force attempts detected on port 22",
            "HTTP flood to specific endpoint suggests L7 DDoS",
            "ICMP tunneling pattern detected (payload size anomalies)",
            "Unusual spike of UDP 53 traffic (DNS amplification hint)",
            "Source IP scanning on multiple destination ports (horizontal scan)",
            "Destination port scanning across many targets (vertical scan)",
            "SMB enumeration or suspicious file share access spikes",
            "ARP spoofing/MITM indicators on local segment",
            "New unauthorized services exposed on non-standard ports",
            "Excessive DHCP requests (possible rogue client or DoS)",
            "DNS TXT record abuse or unusually large responses",
            "Outbound connections to TOR exit nodes detected",
            "DoH/DoT usage spike bypassing corporate DNS",
            "High entropy in outbound payloads suggests covert channel",
            "Unusual increase in reset packets (RST) during business hours"
            ]),
            flows=df.sample(1).to_dict("records"),
        )]
