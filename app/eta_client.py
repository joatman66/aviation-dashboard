import os
import logging
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET

import requests

log = logging.getLogger(__name__)


def _build_xml(opstype: str, creds: Dict[str, str], extra_params: Optional[Dict[str, str]] = None) -> str:
    params = dict(creds)
    if extra_params:
        params.update({k: v for k, v in extra_params.items() if v is not None})

    inner = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    return f'<etaws><operation opstype="{opstype}">export</operation><parameters>{inner}</parameters></etaws>'


def _call_eta(base_url: str, opstype: str, creds: Dict[str, str], extra_params: Optional[Dict[str, str]] = None) -> str:
    xml = _build_xml(opstype, creds, extra_params)
    resp = requests.get(base_url, params={"xmldata": xml}, timeout=30)
    resp.raise_for_status()
    return resp.text.strip()


def _parse_aircraft_xml(xml_text: str) -> List[Dict]:
    """
    Parse ETA 'aircraft' export.

    We derive:
      - tail from AIRCRAFT (fallback NNUMBER/CALL_NUMBER)
      - aircraft_type from RESOURCE_TYPE (fallback AIRCRAFT_CLASS/DESCRIPTION)
      - hobbs from HOBBS
    """
    root = ET.fromstring(xml_text)

    aircraft_nodes = root.findall(".//AIRCRAFT")
    if not aircraft_nodes and root.tag.upper() == "AIRCRAFT":
        aircraft_nodes = [root]

    results: List[Dict] = []

    for node in aircraft_nodes:
        def txt(tag: str) -> str:
            return (node.findtext(tag) or "").strip()

        tail = txt("AIRCRAFT") or txt("NNUMBER") or txt("CALL_NUMBER")

        resource_type = txt("RESOURCE_TYPE")
        aircraft_class = txt("AIRCRAFT_CLASS")
        description = txt("DESCRIPTION")

        # Canonical display value used everywhere in UI
        aircraft_type = resource_type or aircraft_class or description

        hobbs_text = txt("HOBBS")
        try:
            hobbs = float(hobbs_text) if hobbs_text else 0.0
        except ValueError:
            hobbs = 0.0

        obsolete_flag = txt("OBSOLETE")
        obsolete = obsolete_flag.lower().startswith("y") if obsolete_flag else False

        results.append(
            {
                "tail": tail,
                "aircraft_type": aircraft_type,
                "resource_type": resource_type,
                "aircraft_class": aircraft_class,
                "description": description,
                "hobbs": hobbs,
                "obsolete": obsolete,
            }
        )

    return results


def _get_base_and_creds(app_config):
    base_url = (
        app_config.get("ETA_BASE_URL")
        or os.getenv("ETA_BASE_URL")
        or "https://apps3.talonsystems.com/tseta/servlet/Talonws"
    )

    creds = {
        "customercode": app_config.get("ETA_CUSTOMER_CODE") or os.getenv("ETA_CUSTOMER_CODE"),
        "accesscode": app_config.get("ETA_ACCESS_CODE") or os.getenv("ETA_ACCESS_CODE"),
        "username": app_config.get("ETA_USERNAME") or os.getenv("ETA_USERNAME"),
    }

    missing = [k for k, v in creds.items() if not v]
    if missing:
        raise RuntimeError(f"Missing ETA credentials: {', '.join(missing)}")

    return base_url, creds


def get_aircraft_raw(app_config) -> List[Dict]:
    """
    Raw list from ETA (no filters). Use only for debugging.
    """
    base_url, creds = _get_base_and_creds(app_config)
    xml_text = _call_eta(base_url, "aircraft", creds, {"aircraftstatus": "Active"})
    return _parse_aircraft_xml(xml_text)


def get_aircraft_summary(app_config) -> List[Dict]:
    """
    Filtered list used by ALL dashboards.

    Filters:
      - tail must exist
      - tail must NOT start with 'T'
    """
    aircraft = get_aircraft_raw(app_config)

    filtered: List[Dict] = []
    for a in aircraft:
        tail = (a.get("tail") or "").strip()
        if not tail:
            continue
        if tail.upper().startswith("T"):
            continue
        filtered.append(a)

    return filtered
