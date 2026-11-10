"""Domain models and the publishing decision for a logistics sender."""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    event: str
    occurred_at: str


@dataclass(frozen=True)
class ProofOfDelivery:
    shipment_id: str
    file_name: str
    checksum: str


@dataclass(frozen=True)
class ShipmentException:
    shipment_id: str
    reason: str
    resolved: bool = False


@dataclass
class Shipment:
    shipment_id: str
    events: List[ShipmentEvent] = field(default_factory=list)
    proof: ProofOfDelivery = None
    exception: ShipmentException = None


def should_publish_delivery_notice(shipment: Shipment) -> bool:
    """Publish only when delivery is observed, proof is present, and no exception remains."""
    delivered = any(item.event == "delivered" for item in shipment.events)
    return delivered and shipment.proof is not None and (
        shipment.exception is None or shipment.exception.resolved
    )
