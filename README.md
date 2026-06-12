# 🚚 Carrier API Health Checker

A Python CLI tool that monitors the availability of carrier (shipping) APIs
by performing HTTP health checks and displaying results in a formatted
console dashboard.

Built for **logistics and e-commerce operations** where carrier API downtime
directly impacts order fulfillment and shipping workflows.

---

## Features

- **Multi-carrier monitoring** — Check multiple carrier endpoints in a single run
- **Health detection** — Distinguishes between healthy responses (2xx, expected 4xx)
  and actual failures (5xx, timeouts, connection errors)
- **Console dashboard** — Color-coded status overview with latency metrics
- **CSV export** — Timestamped reports for historical tracking
- **Verbose mode** — Detailed pre/post check output with performance indicators
- **Configurable logging** — 5 log levels (DEBUG→CRITICAL), console + file output
- **Flexible CLI** — Custom config files, output directories, and runtime flags

## Carriers Monitored (default config)

| Carrier | Endpoint Type | Region |
|---------|--------------|--------|
| Colissimo (La Poste) | Tracking API | France |
| La Poste | Developer Portal Status | France |
| DHL Express | MyDHL API (sandbox) | Global |
| DHL eCommerce | Parcel API | EU (NL) |
| GLS | ShipIT REST API | EU |
| UPS | OAuth Token endpoint | Global |

## Quick Start

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/Vincecodeur/carrier-api-health-checker.git
cd carrier-api-health-checker
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt