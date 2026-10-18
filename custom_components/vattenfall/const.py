"""Constants for the Vattenfall Dynamic Tariffs integration."""

DOMAIN = "vattenfall"

CONF_API_KEY = "api_key"

API_ENDPOINT = "https://api.vattenfall.nl/api/vfnl/consumptions/v1/DynamicTariff"

DEFAULT_SCAN_INTERVAL = 1800  # 30 minutes in seconds

ATTR_HOURLY_PRICES = "hourly_prices"
ATTR_TODAY_PRICES = "today_prices"
ATTR_TOMORROW_PRICES = "tomorrow_prices"
ATTR_CHEAPEST_HOUR = "cheapest_hour"
ATTR_HIGHEST_HOUR = "highest_hour"
ATTR_AVERAGE_PRICE = "average_price"
ATTR_PRICE_DETAILS = "price_details"
