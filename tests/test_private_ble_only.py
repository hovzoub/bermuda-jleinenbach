"""Tests for Bermuda's private-BLE-only ingestion mode."""

from __future__ import annotations

from types import SimpleNamespace

from homeassistant.core import HomeAssistant

from custom_components.bermuda.bermuda_irk import BermudaIrkManager
from custom_components.bermuda.const import ADDR_TYPE_PRIVATE_BLE_DEVICE, IrkTypes
from custom_components.bermuda.coordinator import BermudaDataUpdateCoordinator


def _coordinator(hass: HomeAssistant) -> BermudaDataUpdateCoordinator:
    coordinator = BermudaDataUpdateCoordinator.__new__(BermudaDataUpdateCoordinator)
    coordinator.hass = hass
    coordinator.private_ble_only = True
    coordinator.metadevices = {}
    coordinator.pb_state_sources = {}
    coordinator.irk_manager = BermudaIrkManager()
    return coordinator


def test_private_ble_only_accepts_current_private_source(hass: HomeAssistant) -> None:
    """Known sources of enrolled Private BLE devices remain ingestible."""
    coordinator = _coordinator(hass)
    coordinator.metadevices["irk"] = SimpleNamespace(
        address_type=ADDR_TYPE_PRIVATE_BLE_DEVICE,
        metadevice_sources=["AA:BB:CC:DD:EE:FF"],
    )

    assert coordinator._should_ingest_advert("aa:bb:cc:dd:ee:ff")


def test_private_ble_only_rejects_unmatched_advert(hass: HomeAssistant) -> None:
    """Ordinary nearby BLE adverts do not create Bermuda devices."""
    coordinator = _coordinator(hass)

    assert not coordinator._should_ingest_advert("AA:BB:CC:DD:EE:FF")


def test_private_ble_only_accepts_matching_rotating_address(hass: HomeAssistant) -> None:
    """Rotating addresses that resolve to an enrolled IRK remain ingestible."""
    coordinator = _coordinator(hass)
    coordinator.irk_manager.scan_device = lambda _address: (True, bytes.fromhex("11" * 16))

    assert coordinator._should_ingest_advert("45:BB:CC:DD:EE:FF")


def test_private_ble_only_rejects_unresolved_rotating_address(hass: HomeAssistant) -> None:
    """Unresolved rotating addresses remain excluded."""
    coordinator = _coordinator(hass)
    coordinator.irk_manager.scan_device = lambda _address: (False, IrkTypes.NO_KNOWN_IRK_MATCH.value)

    assert not coordinator._should_ingest_advert("45:BB:CC:DD:EE:FF")
