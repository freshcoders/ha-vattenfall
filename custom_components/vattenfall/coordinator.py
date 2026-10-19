"""DataUpdateCoordinator for Vattenfall Dynamic Tariffs."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import zoneinfo

import async_timeout
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .const import API_ENDPOINT, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class VattenfallDataCoordinator(DataUpdateCoordinator[dict]):
    """Class to manage fetching Vattenfall dynamic tariff data."""

    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        """Initialize."""
        self.api_key = api_key
        self._raw_data: list | None = None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Vattenfall API endpoint."""
        session = async_get_clientsession(self.hass)
        headers = {"ocp-apim-subscription-key": self.api_key}

        try:
            async with async_timeout.timeout(30):
                response = await session.get(API_ENDPOINT, headers=headers)
                if response.status != 200:
                    text = await response.text()
                    raise UpdateFailed(
                        f"Error communicating with Vattenfall API: HTTP {response.status} - {text}"
                    )
                raw_data = await response.json()
        except Exception as err:
            raise UpdateFailed(f"Error fetching Vattenfall tariffs: {err}") from err

        self._raw_data = raw_data
        return self._process_tariff_data(raw_data)

    @callback
    def async_start_hourly_refresh(self) -> CALLBACK_TYPE:
        """Recompute the current price right after each hour starts.

        The API is only polled every 30 minutes, so without this the current
        price can lag the new hour by up to half an hour.
        """

        @callback
        def _hour_changed(_now: datetime) -> None:
            if self._raw_data is not None:
                self.async_set_updated_data(self._process_tariff_data(self._raw_data))

        return async_track_time_change(self.hass, _hour_changed, minute=0, second=1)

    def _process_tariff_data(self, raw_data: list) -> dict:
        """Process and structure raw tariff JSON into sensors data."""
        electricity_raw = None
        gas_raw = None

        for item in raw_data:
            if item.get("product") == "E":
                electricity_raw = item
            elif item.get("product") == "G":
                gas_raw = item

        now = dt_util.now()
        today_date = now.date()
        tomorrow_date = today_date + timedelta(days=1)

        result: dict = {"electricity": {}, "gas": {}}

        # Process Electricity (FlexPrijsStroom)
        if electricity_raw and "tariffData" in electricity_raw:
            records = []
            for entry in electricity_raw["tariffData"]:
                if entry.get("isMissingPeriod") or "amountInclVat" not in entry:
                    continue
                start_dt = dt_util.parse_datetime(entry["startTime"])
                end_dt = dt_util.parse_datetime(entry["endTime"])
                
                details_dict = {}
                for d in entry.get("details", []):
                    details_dict[d.get("type", "UNKNOWN")] = {
                        "amountInclVat": round(float(d.get("amountInclVat", 0)), 5),
                        "amountExclVat": round(float(d.get("amountExclVat", 0)), 5),
                    }

                records.append({
                    "start": entry["startTime"],
                    "end": entry["endTime"],
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "price": round(float(entry["amountInclVat"]), 4),
                    "price_excl_vat": round(float(entry["amountExclVat"]), 4),
                    "cheapest": entry.get("cheapestOfDay", False),
                    "details": details_dict,
                })

            records.sort(key=lambda x: x["start"])

            # Find current hour
            current_entry = None
            for r in records:
                if r["start_dt"] and r["end_dt"] and r["start_dt"] <= now < r["end_dt"]:
                    current_entry = r
                    break

            if not current_entry and records:
                current_entry = records[-1]

            today_records = [
                r for r in records if r["start_dt"] and r["start_dt"].astimezone(now.tzinfo).date() == today_date
            ]
            tomorrow_records = [
                r for r in records if r["start_dt"] and r["start_dt"].astimezone(now.tzinfo).date() == tomorrow_date
            ]

            # All upcoming/future hours starting from now (current hour + rest of today + tomorrow)
            upcoming_records = [
                r for r in records if r["end_dt"] and r["end_dt"] > now
            ]

            # Today statistics
            cheapest_today = min(today_records, key=lambda x: x["price"]) if today_records else None
            highest_today = max(today_records, key=lambda x: x["price"]) if today_records else None
            avg_today = (
                round(sum(r["price"] for r in today_records) / len(today_records), 4)
                if today_records
                else None
            )

            # Tomorrow statistics (available after ~13:00-14:00 CET)
            tomorrow_valid = len(tomorrow_records) >= 23
            cheapest_tomorrow = min(tomorrow_records, key=lambda x: x["price"]) if tomorrow_valid else None
            highest_tomorrow = max(tomorrow_records, key=lambda x: x["price"]) if tomorrow_valid else None
            avg_tomorrow = (
                round(sum(r["price"] for r in tomorrow_records) / len(tomorrow_records), 4)
                if tomorrow_valid
                else None
            )

            result["electricity"] = {
                "current_price": current_entry["price"] if current_entry else None,
                "current_price_excl_vat": current_entry["price_excl_vat"] if current_entry else None,
                "is_cheapest": current_entry["cheapest"] if current_entry else False,
                "details": current_entry["details"] if current_entry else {},
                "hourly_prices": [
                    {
                        "from": r["start"],
                        "to": r["end"],
                        "price": r["price"],
                        "price_excl_vat": r["price_excl_vat"],
                        "cheapest": r["cheapest"],
                    }
                    for r in records[-48:]
                ],
                "today_prices": [
                    {"from": r["start"], "to": r["end"], "price": r["price"], "cheapest": r["cheapest"]}
                    for r in today_records
                ],
                "tomorrow_prices": [
                    {"from": r["start"], "to": r["end"], "price": r["price"], "cheapest": r["cheapest"]}
                    for r in tomorrow_records
                ],
                "upcoming_prices": [
                    {"from": r["start"], "to": r["end"], "price": r["price"], "cheapest": r["cheapest"]}
                    for r in upcoming_records
                ],
                "tomorrow_valid": tomorrow_valid,
                "cheapest_hour_today": cheapest_today["start"] if cheapest_today else None,
                "cheapest_price_today": cheapest_today["price"] if cheapest_today else None,
                "highest_hour_today": highest_today["start"] if highest_today else None,
                "highest_price_today": highest_today["price"] if highest_today else None,
                "average_price_today": avg_today,
                "cheapest_hour_tomorrow": cheapest_tomorrow["start"] if cheapest_tomorrow else None,
                "cheapest_price_tomorrow": cheapest_tomorrow["price"] if cheapest_tomorrow else None,
                "highest_hour_tomorrow": highest_tomorrow["start"] if highest_tomorrow else None,
                "highest_price_tomorrow": highest_tomorrow["price"] if highest_tomorrow else None,
                "average_price_tomorrow": avg_tomorrow,
            }

        # Process Gas (FlexPrijsGas)
        gas_entries = [
            e for e in (gas_raw or {}).get("tariffData", [])
            if "amountInclVat" in e and "amountExclVat" in e
        ]
        if gas_entries:
            latest_gas = gas_entries[-1]
            gas_history = []
            for entry in gas_entries[-14:]:
                gas_history.append({
                    "date": entry["startTime"][:10],
                    "price": round(float(entry["amountInclVat"]), 4),
                    "price_excl_vat": round(float(entry["amountExclVat"]), 4),
                })

            gas_details = {}
            for d in latest_gas.get("details", []):
                gas_details[d.get("type", "UNKNOWN")] = {
                    "amountInclVat": round(float(d.get("amountInclVat", 0)), 5),
                    "amountExclVat": round(float(d.get("amountExclVat", 0)), 5),
                }

            result["gas"] = {
                "current_price": round(float(latest_gas["amountInclVat"]), 4),
                "current_price_excl_vat": round(float(latest_gas["amountExclVat"]), 4),
                "date": latest_gas["startTime"][:10],
                "details": gas_details,
                "history": gas_history,
            }

        return result
