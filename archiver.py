import logging
import subprocess
from pathlib import Path
from time import sleep

import yaml
import pendulum
from selenium.common.exceptions import InvalidSessionIdException

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
        filename = f"./archives/{scrap_date.year}/{scrap_date.month:02}/{scrap_date.to_date_string()}.pdf"
        try:
            scraper.download_journal(date_string, dl_path=str(folder))
            logging.info("created %s (launching merger)", folder)
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

def main_scrap_missing():
    config = yaml.safe_load(open("config.yaml"))
    dates = set()
    date = pendulum.local(2020, 2, 1)
    while date < pendulum.local(2024, 11, 5):
        dates.add(date.to_date_string())
        date += pendulum.duration(days=1)
    old_diff = set()
    new_diff = dates
    while old_diff != new_diff:
        old_diff = new_diff
        pdfs = set([pdf.name.replace('.pdf', '') for pdf in Path("./archives").glob("*/*/*.pdf")])
        new_diff = dates - pdfs

        logging.info("launching scraper")
        scraper = KazetennScraper()
        for name, value in config["cookies"].items():
            scraper.add_cookie(name, value)
        if "edition" in config:
            scraper.DEFAULT_EDITION = config["edition"]
        try:
            for date_string in sorted(new_diff):
                if date_string[5:] == '01-01' or date_string[5:] == '05-01' or date_string[5:] == '12-25':
                    logging.info("skipping %s", date_string)
                    continue
                scrap_date = pendulum.parse(date_string)
                folder = Path(f"./archives/{scrap_date.year}/{scrap_date.month:02}/{scrap_date.day:02}")
                folder.mkdir(parents=True, exist_ok=True)
                filename = f"./archives/{scrap_date.year}/{scrap_date.month:02}/{scrap_date.to_date_string()}.pdf"
                try:
                    scraper.download_journal(date_string, dl_path=str(folder))
                    logging.info("created %s (launching merger)", folder)
                    subprocess.Popen(["ruby", "merger.rb", str(folder), filename])
                except InvalidSessionIdException as e:
                    logging.error("failed to create %s with error: %s", filename, e.__class__.__name__)
                    logging.error("stopping scraping because of error: %s", repr(e))
                    break
                except Exception as e:
                    logging.error("failed to create %s with error: %s", filename, repr(e))
        except KeyboardInterrupt:
            logging.info("got keyboard interrupt signal, shutting down")
        del scraper
        logging.info("shutting down and trying again in 5mn")
        sleep(300)
    logging.info("No new file downloaded, ending this")

if __name__ == "__main__":
    main_scrap_missing()
