"""Create device_tracker entities for Bermuda devices."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import BaseScannerEntity
from homeassistant.const import STATE_HOME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import SIGNAL_DEVICE_NEW
from .entity import BermudaEntity

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import BermudaConfigEntry
    from .coordinator import BermudaDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BermudaConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Load Device Tracker entities for a config entry."""
    coordinator: BermudaDataUpdateCoordinator = entry.runtime_data.coordinator

    created_devices = []  # list of devices we've already created entities for

    @callback
    def device_new(address: str) -> None:
        """
        Create entities for newly-found device.

        Called from the data co-ordinator when it finds a new device that needs
        to have sensors created. Not called directly, but via the dispatch
        facility from HA.
        Make sure you have a full list of scanners ready before calling this.
        """
        if address not in created_devices:
            # Check for duplicate entities with old address formats before creating new ones
            old_address = coordinator.check_for_duplicate_entities(address)
            if old_address:
                coordinator.cleanup_old_entities_for_device(old_address, address)

            entities = []
            entities.append(BermudaDeviceTracker(coordinator, entry, address))
            # We set update before add to False because we are being
            # call(back(ed)) from the update, so causing it to call another would be... bad.
            async_add_devices(entities, False)
            created_devices.append(address)
        else:
            # _LOGGER.debug(
            #     "Ignoring create request for existing dev_tracker %s", address
            # )
            pass
        # tell the co-ord we've done it.
        coordinator.device_tracker_created(address)  # type: ignore[no-untyped-call]

    # Connect device_new to a signal so the coordinator can call it
    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_DEVICE_NEW, device_new))

    # Now we must tell the co-ord to do initial refresh, so that it will call our callback.
    # await coordinator.async_config_entry_first_refresh()


class BermudaDeviceTracker(BermudaEntity, BaseScannerEntity):
    """A trackable Bermuda Device."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "tracker"
    _attr_source_type = SourceType.BLUETOOTH_LE
    # Override BaseTrackerEntity's default DIAGNOSTIC category.
    # Bermuda's device_tracker is the PRIMARY function (location tracking for Person entities),
    # not diagnostic information about a device.
    # BaseTrackerEntity narrows Entity's EntityCategory | None to EntityCategory,
    # but we intentionally want None here (no category = primary entity).
    _attr_entity_category = None  # type: ignore[assignment]

    # Exclude the "scanner" and "area" attributes from the recorder database.
    # They duplicate data already available from dedicated sensor entities
    # (BermudaSensor, BermudaSensorScanner), and recording them here creates
    # redundant DB writes on every area change. The state (home/not_home or the
    # associated zone) and the scanner attributes in_zones and source_type are
    # still recorded; in_zones changes with the state or the zone setup, not per
    # advertisement.
    _unrecorded_attributes = frozenset({"scanner", "area"})

    @property
    def unique_id(self) -> str:
        """
        "Uniquely identify this sensor so that it gets stored in the entity_registry,
        and can be maintained / renamed etc by the user.
        """
        return self._device.unique_id  # type: ignore[return-value]

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return extra state attributes for this device."""
        _scannername = self._device.area_advert.name if self._device.area_advert is not None else None
        return {"scanner": _scannername, "area": self._device.area_name}

    @property
    def is_connected(self) -> bool:
        """Return True while Bermuda places the device at home (seen by a scanner recently)."""
        return self._device.zone == STATE_HOME

    @property
    def icon(self) -> str:
        """Return device icon."""
        return "mdi:bluetooth-connect" if self._device.zone == STATE_HOME else "mdi:bluetooth-off"
