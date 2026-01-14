from typing import List, Dict, Optional
from app.models.schemas import (
    VerdictRequest, VerdictResponse, SeverityLevel,
    AlertType, ModelFindingsNormal, ModelFindingsAbnormal
)
from app.services.severity_strategy import SeverityStrategy, ConfidenceBasedStrategy
from app.config import Config
from app.utils.logger import setup_logger


logger = setup_logger(__name__)


# Well-known port → service name
PORT_SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC",
    6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
}


def _infer_attack_context(attack_type: str, profile: Optional[Dict]) -> dict:
    """
    Analyze traffic profile to infer what kind of attack is happening,
    producing a dynamic summary, detail, and tailored actions —
    even when the CNN labels everything as 'DoS'.
    """
    if not profile:
        profile = {}

    top_ports = profile.get("top_dst_ports", {})
    unique_ports = profile.get("unique_dst_ports", 0)
    unique_srcs = profile.get("unique_src_ips", 0)
    protocols = profile.get("protocols", {})
    avg_fwd_bytes = profile.get("avg_fwd_bytes", 0)
    avg_duration = profile.get("avg_flow_duration_us", 0)

    # Identify targeted services
    targeted_services = []
    for port, count in sorted(top_ports.items(), key=lambda x: x[1], reverse=True)[:3]:
        svc = PORT_SERVICES.get(port, f"port {port}")
        targeted_services.append(svc)

    # Determine the primary targeted port
    primary_port = int(list(top_ports.keys())[0]) if top_ports else 0
    primary_svc = PORT_SERVICES.get(primary_port, f"port {primary_port}")

    # --- Heuristic: infer the real attack scenario from traffic shape ---

    # SSH/FTP brute force pattern: many flows to port 22/21, small packets
    if primary_port in (22, 21, 23) and avg_fwd_bytes < 5000:
        return {
            "label": "Brute-Force Authentication Attack",
            "summary": f"Brute-force attack targeting {primary_svc} service detected",
            "detail": (
                f"High volume of connections targeting {primary_svc} (port {primary_port}) with "
                f"small payload sizes ({avg_fwd_bytes:.0f} bytes avg), consistent with automated "
                f"credential stuffing or password brute-force tools. "
                f"{unique_srcs} unique source IP(s) observed."
            ),
            "actions": [
                f"Enforce account lockout on the {primary_svc} service",
                f"Block source IPs with repeated failed {primary_svc} login attempts",
                f"Enable multi-factor authentication for {primary_svc} access",
                f"Review {primary_svc} authentication logs for compromised accounts",
            ],
        }

    # Web attack pattern: port 80/443/8080
    if primary_port in (80, 443, 8080, 8443):
        return {
            "label": "Web Application Attack",
            "summary": f"Malicious activity targeting {primary_svc} web service detected",
            "detail": (
                f"Suspicious traffic directed at {primary_svc} (port {primary_port}) "
                f"with {avg_fwd_bytes:.0f} bytes average payload size. "
                f"This may include exploit attempts, SQL injection, XSS, or directory traversal. "
                f"{unique_srcs} unique source IP(s) involved across {unique_ports} destination ports."
            ),
            "actions": [
                "Review web application firewall (WAF) logs for attack payloads",
                f"Inspect {primary_svc} server access logs for exploit patterns",
                "Patch and update the targeted web application stack",
                "Block attacking source IPs at the reverse proxy",
            ],
        }

    # SMTP attack: port 25
    if primary_port == 25:
        return {
            "label": "SMTP / Email Service Attack",
            "summary": "Attack targeting mail server (SMTP) detected",
            "detail": (
                f"Anomalous traffic to SMTP service (port 25) detected. "
                f"This may indicate email relay abuse, spam injection, or exploitation of "
                f"mail server vulnerabilities. {unique_srcs} source IP(s) observed."
            ),
            "actions": [
                "Review SMTP server logs for unauthorized relay attempts",
                "Ensure open relay is disabled on the mail server",
                "Block suspicious source IPs at the mail gateway",
                "Check for known SMTP server vulnerabilities and patch",
            ],
        }

    # SMB / NetBIOS attack: port 445/139
    if primary_port in (445, 139):
        return {
            "label": "SMB / NetBIOS Exploitation",
            "summary": "Attack targeting SMB/NetBIOS file sharing service detected",
            "detail": (
                f"High volume of traffic to SMB service (port {primary_port}) detected. "
                f"This pattern is consistent with lateral movement, ransomware propagation, "
                f"or exploitation of SMB vulnerabilities (e.g., EternalBlue). "
                f"{unique_srcs} source IP(s) involved."
            ),
            "actions": [
                "Isolate affected hosts from the network segment",
                "Disable unnecessary SMB shares and services",
                "Scan for EternalBlue and related SMB vulnerabilities",
                "Check for signs of ransomware or lateral movement",
            ],
        }

    # Database attack
    if primary_port in (3306, 5432, 1433, 1521, 27017, 6379):
        return {
            "label": "Database Service Attack",
            "summary": f"Attack targeting {primary_svc} database service detected",
            "detail": (
                f"Suspicious connections to {primary_svc} (port {primary_port}) detected. "
                f"This may indicate unauthorized database access attempts, SQL injection "
                f"via direct connection, or brute-force of database credentials. "
                f"{unique_srcs} source IP(s) involved."
            ),
            "actions": [
                f"Review {primary_svc} access logs for unauthorized queries",
                "Ensure database is not exposed to untrusted networks",
                f"Rotate {primary_svc} credentials as a precaution",
                "Verify database firewall rules restrict access to authorized hosts only",
            ],
        }

    # RDP attack: port 3389
    if primary_port == 3389:
        return {
            "label": "Remote Desktop Attack",
            "summary": "Brute-force or exploitation targeting RDP service detected",
            "detail": (
                f"High volume of connections to Remote Desktop (port 3389). "
                f"This is commonly targeted for credential brute-forcing or exploitation "
                f"of RDP vulnerabilities (e.g., BlueKeep). {unique_srcs} source IP(s) observed."
            ),
            "actions": [
                "Enable Network Level Authentication (NLA) on RDP",
                "Restrict RDP access to VPN-only or specific IP ranges",
                "Review Windows Event logs for failed logon attempts",
                "Consider disabling RDP if not essential",
            ],
        }

    # Port scan pattern: many unique destination ports
    if unique_ports > 20:
        return {
            "label": "Network Reconnaissance / Port Scan",
            "summary": f"Port scanning activity detected across {unique_ports} ports",
            "detail": (
                f"Traffic directed at {unique_ports} unique destination ports, "
                f"indicating systematic port enumeration or network reconnaissance. "
                f"Top targeted services: {', '.join(targeted_services[:3]) if targeted_services else 'various'}. "
                f"{unique_srcs} source IP(s) involved."
            ),
            "actions": [
                "Log and monitor the scanning source IPs",
                "Verify that only necessary ports are exposed externally",
                "Add scanning sources to a watch list",
                "Review firewall rules to restrict inbound access",
            ],
        }

    # DDoS pattern: many source IPs
    if unique_srcs > 10:
        return {
            "label": "Distributed Attack",
            "summary": f"Distributed attack from {unique_srcs} source IPs detected",
            "detail": (
                f"Anomalous traffic from {unique_srcs} unique source IPs "
                f"targeting {primary_svc} (port {primary_port}). "
                f"The distributed nature suggests coordinated botnet activity or DDoS. "
                f"Average payload: {avg_fwd_bytes:.0f} bytes."
            ),
            "actions": [
                "Activate rate limiting and traffic shaping",
                "Block or null-route top attacking source IP ranges",
                f"Enable SYN cookies on {primary_svc} service",
                "Coordinate with ISP for upstream traffic filtering if needed",
            ],
        }

    # Generic / DoS fallback with service context
    svc_context = f"targeting {primary_svc} (port {primary_port})" if primary_port else "across network services"
    return {
        "label": f"Anomalous Traffic — {primary_svc}" if primary_port else "Anomalous Network Traffic",
        "summary": f"Suspicious network activity {svc_context} detected",
        "detail": (
            f"The classifier flagged anomalous flow patterns {svc_context}. "
            f"Average forward payload: {avg_fwd_bytes:.0f} bytes, "
            f"average flow duration: {avg_duration / 1e6:.1f}s. "
            f"{unique_srcs} unique source IP(s), {unique_ports} unique destination port(s). "
            f"Targeted services: {', '.join(targeted_services) if targeted_services else 'unknown'}."
        ),
        "actions": [
            f"Investigate traffic to {primary_svc} for exploit or abuse patterns",
            "Capture additional packets for deep inspection",
            "Review IDS/IPS signatures for the flagged traffic",
            "Escalate to security team if patterns persist",
        ],
    }


class VerdictService:
    def __init__(self, config: Config, severity_strategy: SeverityStrategy = None):
        self.config = config
        self.severity_strategy = severity_strategy or ConfidenceBasedStrategy()

    def generate_verdict(self, request: VerdictRequest) -> VerdictResponse:
        findings = request.modelFindings

        if findings.get("status") == "normal":
            return self._handle_normal(findings)

        return self._handle_abnormal(findings, request.context)

    def _handle_normal(self, findings: dict) -> VerdictResponse:
        validated = ModelFindingsNormal(**findings)
        flow_count = validated.flow_count

        if flow_count == 0:
            explanation = (
                "No network flows could be extracted from the capture file. "
                "The PCAP may be too small, corrupted, or contain only non-TCP/UDP traffic."
            )
        else:
            explanation = (
                f"The 2D CNN + OpenMax classifier analyzed {flow_count:,} network flows "
                f"and classified the traffic as benign with {validated.confidence:.1%} average confidence. "
                f"No significant attack patterns were identified in the captured traffic."
            )

        return VerdictResponse(
            verdict=SeverityLevel.LOW,
            summary="Normal network behavior detected",
            explanation=explanation,
            recommendedActions=["Continue standard network monitoring"],
            alertsTriggered=[]
        )

    def _handle_abnormal(self, findings: dict, context) -> VerdictResponse:
        validated = ModelFindingsAbnormal(**findings)

        severity = self.severity_strategy.calculate(validated, context, self.config)
        alerts = self._get_alerts(severity)

        # Use traffic profile for dynamic, context-aware messaging
        attack_ctx = _infer_attack_context(
            validated.attack_type,
            validated.traffic_profile,
        )

        summary = f"{attack_ctx['summary']} — {severity.value} severity"
        actions = attack_ctx["actions"][:]
        if severity == SeverityLevel.CRITICAL:
            actions.append("Escalate immediately to incident response team")

        explanation = self._build_explanation(validated, context, severity, attack_ctx)

        logger.warning("Abnormal traffic detected", extra={
            "attack_type": validated.attack_type,
            "inferred_label": attack_ctx["label"],
            "severity": severity.value,
            "confidence": validated.confidence,
            "attack_ratio": validated.attack_ratio,
        })

        return VerdictResponse(
            verdict=severity,
            summary=summary,
            explanation=explanation,
            inferredAttack=attack_ctx["label"],
            recommendedActions=actions,
            alertsTriggered=alerts
        )

    def _get_alerts(self, severity: SeverityLevel) -> List[AlertType]:
        alert_map = {
            SeverityLevel.LOW: [],
            SeverityLevel.MEDIUM: [AlertType.SOC],
            SeverityLevel.HIGH: [AlertType.SOC, AlertType.FIREWALL],
            SeverityLevel.CRITICAL: [AlertType.SOC, AlertType.FIREWALL, AlertType.ADMIN, AlertType.SIEM]
        }
        return alert_map[severity]

    def _build_explanation(
        self,
        findings: ModelFindingsAbnormal,
        context,
        severity: SeverityLevel,
        attack_ctx: dict,
    ) -> str:
        total = findings.flow_count
        attack_pct = findings.attack_ratio * 100
        dist = findings.class_distribution or {}

        dist_parts = []
        for cls, count in sorted(dist.items(), key=lambda x: x[1], reverse=True):
            pct = (count / max(total, 1)) * 100
            dist_parts.append(f"{cls}: {count:,} ({pct:.1f}%)")
        dist_str = ", ".join(dist_parts) if dist_parts else "N/A"

        return (
            f"The 2D CNN + OpenMax classifier analyzed {total:,} network flows. "
            f"{attack_pct:.1f}% of flows ({int(total * findings.attack_ratio):,} flows) were flagged as malicious. "
            f"{attack_ctx['detail']} "
            f"Flow classification breakdown — {dist_str}. "
            f"Context: {context.networkZone.value} network zone, {context.assetCriticality.value} criticality asset. "
            f"Final severity: {severity.value}."
        )
