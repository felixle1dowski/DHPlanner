from dataclasses import dataclass
from qgis.core import QgsPointXY

@dataclass(frozen=True)
class NodeInformation:
    is_ap: bool
    ap_id: int or None
    coordinates: QgsPointXY