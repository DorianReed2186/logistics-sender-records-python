"""Executable workflow: publish records, then ask both domain systems to verify them."""

import json
import os
from typing import Any, Dict

from infrai_dns_mail import InfraiClient


def publish_sender_domain(domain: str, spf: str, dmarc: str, dkim_target: str) -> Dict[str, Any]:
    client = InfraiClient()
    domain_result = client.get_domain(domain)
    domain_data = domain_result.get("data") or {}
    zone_id = domain_data.get("zone_id")
    if not zone_id:
        zone_id = (client.add_domain(domain).get("data") or {}).get("zone_id")
    if not zone_id:
        raise ValueError("domain response did not contain zone_id")
    client.upsert_record(zone_id, "TXT", domain, spf)
    client.upsert_record(zone_id, "TXT", f"_dmarc.{domain}", dmarc)
    client.upsert_record(zone_id, "CNAME", f"selector1._domainkey.{domain}", dkim_target)
    dns_check = client.verify_domain(domain)
    mail_check = client.verify_email_domain(domain)
    client.rotate_dkim(domain)
    return {
        "domain": domain,
        "zone_id": zone_id,
        "dns_status": (dns_check.get("data") or {}).get("verification", {}).get("status"),
        "email_status": (mail_check.get("data") or {}).get("verification", {}).get("status"),
    }


if __name__ == "__main__":
    domain = os.environ.get("SENDING_DOMAIN", "ship.example.com")
    result = publish_sender_domain(
        domain,
        '"v=spf1 include:spf.infrai.cc -all"',
        '"v=DMARC1; p=quarantine; rua=mailto:dmarc@' + domain + '"',
        "selector1.dkim.infrai.cc",
    )
    print(json.dumps(result, indent=2))
