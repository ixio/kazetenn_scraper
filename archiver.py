import logging
import subprocess
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


def scrap_from_date(scraper, scrap_date):
    config = yaml.safe_load(open("config.yaml"))
    for name, value in config["cookies"].items():
        scraper.add_cookie(name, value)
    if "edition" in config:
        scraper.DEFAULT_EDITION = config["edition"]

    # TODO : the simplest is perhaps to try the page here and let the human connect before trying realy scraping
    #scraper.browser.get(
    #    f"https://www.ouest-france.fr/premium/journal/journal-ouest-france/{scrap_date.to_date_string()}/?edition={config["edition"]}"
    #)
    #input("Press Enter to continue...")

    logging.info("start scraping with date %s", scrap_date.to_date_string())
    while scrap_date < pendulum.tomorrow():
        date_string = scrap_date.to_date_string()
        folder = Path(f"./archives/{scrap_date.year}/{scrap_date.month:02}/{scrap_date.day:02}")
        folder.mkdir(parents=True, exist_ok=True)
        try:
            scraper.download_journal(date_string, dl_path=str(folder))
            logging.info("created %s (launching merger)", folder)
            filename = f"./archives/{scrap_date.year}/{scrap_date.month:02}/{scrap_date.to_date_string()}.pdf"
            subprocess.Popen(["ruby", "merger.rb", str(folder), filename])
        except Exception as e:
            logging.error("failed to create %s with error: %s(%s)", folder, e.__class__.__name__, e)

        scrap_date += pendulum.duration(days=1)


def main():
    scrap_date = FIRST_DATE
    while scrap_date < pendulum.local(2024, 10, 5):
        pdfs = sorted([pdf.name for pdf in Path("./archives").glob("*/*/*.pdf")])
        if pdfs != []:
            scrap_date = pendulum.parse(pdfs[-1].split(".")[0]) + pendulum.duration(days=1)
        logging.info("launching scraper")
        scraper = KazetennScraper()
        try:
            scrap_from_date(scraper, scrap_date)
        except KeyboardInterrupt:
            logging.info("got keyboard interrupt signal, shutting down")
        del scraper
        logging.info("shutting down and trying again in 5mn")
        sleep(300)

if __name__ == "__main__":
    main()
