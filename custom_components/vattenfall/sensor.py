"""Sensor platform for Vattenfall Dynamic Tariffs integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVERAGE_PRICE,
    ATTR_CHEAPEST_HOUR,
    ATTR_HIGHEST_HOUR,
    ATTR_HOURLY_PRICES,
    ATTR_PRICE_DETAILS,
    ATTR_TODAY_PRICES,
    ATTR_TOMORROW_PRICES,
    DOMAIN,
)
from .coordinator import VattenfallDataCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vattenfall sensor entities based on a config entry."""
    coordinator: VattenfallDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        VattenfallElectricitySensor(coordinator, entry),
    ]

    # Only add gas sensor if gas data is present in account/API
    if coordinator.data.get("gas", {}).get("current_price") is not None:
        entities.append(VattenfallGasSensor(coordinator, entry))

    async_add_entities(entities)


class VattenfallBaseSensor(CoordinatorEntity[VattenfallDataCoordinator], SensorEntity):
    """Base sensor for Vattenfall."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: VattenfallDataCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Vattenfall Dynamic Tariffs",
            manufacturer="Vattenfall",
            model="FlexPrijs",
            entry_type=DeviceEntryType.SERVICE,
        )


class VattenfallElectricitySensor(VattenfallBaseSensor):
    """Sensor for current electricity dynamic rate."""

    _attr_translation_key = "electricity_price"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR/kWh"
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:lightning-bolt"

    def __init__(
        self, coordinator: VattenfallDataCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize electricity price sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_electricity_price"

    @property
    def native_value(self) -> float | None:
        """Return the current hour dynamic price."""
        return self.coordinator.data.get("electricity", {}).get("current_price")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return dynamic electricity price attributes and forecast."""
        elec = self.coordinator.data.get("electricity", {})
        return {
            ATTR_HOURLY_PRICES: elec.get("hourly_prices", []),
            ATTR_TODAY_PRICES: elec.get("today_prices", []),
            ATTR_TOMORROW_PRICES: elec.get("tomorrow_prices", []),
            "upcoming_prices": elec.get("upcoming_prices", []),
            "tomorrow_valid": elec.get("tomorrow_valid", False),
            ATTR_CHEAPEST_HOUR: elec.get("cheapest_hour_today"),
            "cheapest_price_today": elec.get("cheapest_price_today"),
            ATTR_HIGHEST_HOUR: elec.get("highest_hour_today"),
            "highest_price_today": elec.get("highest_price_today"),
            ATTR_AVERAGE_PRICE: elec.get("average_price_today"),
            "cheapest_hour_tomorrow": elec.get("cheapest_hour_tomorrow"),
            "cheapest_price_tomorrow": elec.get("cheapest_price_tomorrow"),
            "highest_hour_tomorrow": elec.get("highest_hour_tomorrow"),
            "highest_price_tomorrow": elec.get("highest_price_tomorrow"),
            "average_price_tomorrow": elec.get("average_price_tomorrow"),
            "is_cheapest_hour": elec.get("is_cheapest", False),
            "price_excl_vat": elec.get("current_price_excl_vat"),
            ATTR_PRICE_DETAILS: elec.get("details", {}),
        }


class VattenfallGasSensor(VattenfallBaseSensor):
    """Sensor for current gas dynamic rate."""

    _attr_translation_key = "gas_price"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR/m³"
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:fire"

    def __init__(
        self, coordinator: VattenfallDataCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize gas price sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_gas_price"

    @property
    def native_value(self) -> float | None:
        """Return the current gas rate."""
        return self.coordinator.data.get("gas", {}).get("current_price")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return gas price attributes."""
        gas = self.coordinator.data.get("gas", {})
        return {
            "date": gas.get("date"),
            "price_excl_vat": gas.get("current_price_excl_vat"),
            "history": gas.get("history", []),
            ATTR_PRICE_DETAILS: gas.get("details", {}),
        }
