# Vattenfall Dynamic Tariffs for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/default)
[![GitHub Release](https://img.shields.io/github/v/release/yourusername/ha-vattenfall)](https://github.com/yourusername/ha-vattenfall/releases)

A custom Home Assistant integration that connects to **Vattenfall Netherlands (FlexPrijs)** to provide real-time, historical, and day-ahead dynamic electricity and gas prices.

Unlike scraping web pages or dealing with captcha-protected logins, this integration communicates directly with Vattenfall's dynamic tariff API using your browser's Azure API Management subscription key (`ocp-apim-subscription-key`). **No login credentials or refresh tokens are required!**

---

## Features

- ⚡ **Dynamic Electricity Rates (`sensor.vattenfall_electricity_price`)**:
  - Current hour's all-in price (€/kWh).
  - Breakdown: spot market price, procurement fee (*inkoopvergoeding*), energy tax (*energiebelasting*), and VAT (BTW).
  - Attributes: 48-hour history/forecast, today's prices, tomorrow's day-ahead prices (published daily around ~14:00 CET).
  - Smart indicators: `cheapest_hour_today`, `highest_hour_today`, `average_price_today`, and `is_cheapest_hour`.
- 🔥 **Dynamic Gas Rates (`sensor.vattenfall_gas_price`)**:
  - Daily dynamic gas rate (€/m³).
  - 14-day history and breakdown.
- 📊 **Home Assistant Energy Dashboard Ready**:
  - Directly selectable as the dynamic price entity for your electricity grid consumption.
- ⚙️ **Config Flow UI**:
  - Easy setup via Home Assistant UI with automatic API key validation.

---

## Prerequisites: Finding your API Key

You only need one key: the `ocp-apim-subscription-key` used by Vattenfall's web portal.

1. In Chrome, Edge, or Brave, open [Vattenfall Dynamische Energieprijzen](https://www.vattenfall.nl/energie/dynamische-energieprijzen/).
2. Press **F12** to open Developer Tools $\rightarrow$ switch to the **Network** tab $\rightarrow$ click **Fetch/XHR**.
3. Refresh the page or click between Today and Tomorrow.
4. Click on the request to `DynamicTariff`.
5. Under **Request Headers**, copy the value of `ocp-apim-subscription-key` (a 32-character string).

---

## Installation

### Method 1: Via HACS (Recommended)

1. Open **HACS** in your Home Assistant.
2. Click the three dots in the top right $\rightarrow$ **Custom repositories**.
3. Add the repository URL: `https://github.com/yourusername/ha-vattenfall`
   - Category: **Integration**
4. Click **Download**, then restart Home Assistant.

### Method 2: Manual Installation

1. Download the `custom_components/vattenfall` folder from this repository.
2. Copy it into your Home Assistant directory under `config/custom_components/vattenfall`.
3. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, go to **Settings** $\rightarrow$ **Devices & Services**.
2. Click **Add Integration** in the bottom right corner.
3. Search for **Vattenfall Dynamic Tariffs**.
4. Paste your `ocp-apim-subscription-key` and click **Submit**.

---

## Energy Dashboard Setup

To track your live dynamic energy costs in the Home Assistant Energy Dashboard:

1. Go to **Settings** $\rightarrow$ **Dashboards** $\rightarrow$ **Energy**.
2. Under **Electricity grid** $\rightarrow$ Edit your Consumption entity.
3. Under **Electricity price**, choose **Use an entity with current price**.
4. Select `sensor.vattenfall_electricity_price`.
5. Click **Save**.

---

## Dashboard Card Example (ApexCharts)

Plot the 48-hour price graph with today's and tomorrow's rates using [apexcharts-card](https://github.com/RomRider/apexcharts-card):

```yaml
type: custom:apexcharts-card
header:
  show: true
  title: Vattenfall Dynamic Electricity Rates
  show_states: true
graph_span: 48h
span:
  start: day
now:
  show: true
  label: Now
series:
  - entity: sensor.vattenfall_electricity_price
    name: Rate (€/kWh)
    type: column
    data_generator: |
      return entity.attributes.hourly_prices.map((entry) => {
        return [new Date(entry.from).getTime(), entry.price];
      });
```

---

## Automation Example: Run Appliances During Cheapest Hour

```yaml
alias: "Turn on EV Charger during cheapest hour"
trigger:
  - platform: template
    value_template: "{{ state_attr('sensor.vattenfall_electricity_price', 'is_cheapest_hour') == true }}"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ev_charger
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
