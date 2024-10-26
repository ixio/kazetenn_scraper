import logging
from pathlib import Path
from time import sleep

import yaml
import pendulum

from kazetenn_scraper import KazetennScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("scraping.log"), logging.StreamHandler()],
)

FIRST_DATE = pendulum.local(2015, 2, 1)


def main(scraper):
    config = yaml.safe_load(open("config.yaml"))
    for name, value in config["cookies"].items():
        scraper.add_cookie(name, value)
    if "edition" in config:
        scraper.DEFAULT_EDITION = config["edition"]

    # Determine at what date we should start
    scrap_date = FIRST_DATE
    pdfs = sorted([pdf.name for pdf in Path("./archives").glob("**/*.pdf")])
    if pdfs != []:
        scrap_date = pendulum.parse(pdfs[-1].split(".")[0]) + pendulum.duration(days=1)

    logging.info("start scraping with date %s" % scrap_date.to_date_string())
    while scrap_date < pendulum.tomorrow():
        date_string = scrap_date.to_date_string()
        folder = Path(f"./archives/{scrap_date.year}/{scrap_date.month:02}")
        folder.mkdir(parents=True, exist_ok=True)
        filepath = folder / f"{date_string}.pdf"
        try:
            scraper.download_journal(date_string, filename=filepath)
            logging.info("created %s" % filepath)
        except Exception as e:
            logging.error("failed to create %s with error: %s" % (filepath, e))
        scrap_date += pendulum.duration(days=1)


if __name__ == "__main__":
    logging.info("launching scraper")
    scraper = KazetennScraper()
    try:
        main(scraper)
    except KeyboardInterrupt:
        logging.info("got keyboard interrupt signal, shutting down")
    del scraper
    sleep(1)