# Kazetenn scraper

## Setup

Install a webdriver for Firefox: https://www.browserstack.com/guide/geckodriver-selenium-python

```bash
pip install poetry
poetry install
```

Create `config.yaml` file using cookie values from browser after log in :
```yaml
cookies:
  datadome: "Get value from browser"
  SESSION_ID: "Get value from browser"
edition: "nord-finistere"
```

## Usage

```bash
# For a one shot download (saves file in current directory)
poetry run python kazetenn_scraper.py 2015-02-13
# For achives downloading
poetry run python archiver.py
```
