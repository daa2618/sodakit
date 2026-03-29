# sodakit

Python library that builds on sodapy

**sodakit** is a Python wrapper that builds upon [sodapy](https://github.com/afeld/sodapy.git) which is a python client for [Socrata Open Data API](https://dev.socrata.com/). 

---

## 🚀 Features

- 🔍 Search and fetch datasets by domain

---

## 🧪 Prerequisites

- Python 3.11+
- `requests` library (installed automatically with pip)
- `dotenv`
- `nltk`
- `sodapy`
- `geopandas`
- `pandas`
- `requests`

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 📦 Installation

Clone and install locally:

```bash
git clone https://github.com/daa2618/sodakit.git
cd sodakit
pip install .
```

Or install directly using pip (once published on PyPI):

```bash
pip install sodakit
```

---

## 🎯 Usage

Here’s how to get started:

```python


from sodakit import MoreSocrataData

domain = "data.cityofnewyork.us"
nyc_client = MoreSocrataData(domain ="data.cityofnewyork.us",
                    domain_id="NYC",
                    app_token = "my_app_token",
                    username = "my_username",
                    password = "my_password")
---
# Get all available agencies in the domain
agencies = nyc_client.ALL_AGENCIES
print(f"The following agencies are found in '{domain}' domain: {', '.join(agencies)}")

---
# Search datasets
matched_datasets= nyc_client.search_available_datasets("housing")
print(f"The following matching datasets were found: {matched_datasets}")
---
# Load data
dataset_id = nyc_client.get_dataset_id_for_dataset_name("NYC Greenhouse Gas Emissions Inventory")
nyc_client.dataset_id = dataset_id

greenhouse_data = nyc_client.try_loading_dataset()

print(greenhouse_data)
---
# Check column description for the same dataset
col_desc = nyc_client.get_column_description_for_dataset()
print(col_desc)
---

```

## 🧪 Running Tests

```bash
poetry install
pytest tests/
```

---

## 🧾 Contributing

Contributions welcome! You can help by:

- Submitting bug reports or feature requests via Issues
- Improving documentation
- Writing tests or fixing bugs
- Extending Functionalities

Please open a PR or reach out via GitHub Issues.

---

## ⚖️ License

This project is licensed under the [MIT License](LICENSE).

---

## 🙋 FAQ

**Q: Do I need an API key?**  
A: Yes, Get the APP_TOKEN, USENAME, PASSWORD from [Socrata Open Data API](https://dev.socrata.com/) and pass it to the client

**Q: Is this an official wrapper?**  
A: No, this is an independent project built around their open API.

---
