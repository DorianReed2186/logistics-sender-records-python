import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from logistics_records import (ProofOfDelivery, Shipment, ShipmentEvent,
                               ShipmentException, should_publish_delivery_notice)


def test_delivery_notice_waits_for_proof_and_resolved_exception():
    shipment = Shipment(
        "SHP-42",
        [ShipmentEvent("SHP-42", "delivered", "2026-10-25T10:00:00Z")],
        ProofOfDelivery("SHP-42", "pod.pdf", "sha256:abc"),
        ShipmentException("SHP-42", "address check", resolved=False),
    )
    assert should_publish_delivery_notice(shipment) is False
    shipment.exception = ShipmentException("SHP-42", "address check", resolved=True)
    assert should_publish_delivery_notice(shipment) is True
