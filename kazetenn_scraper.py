import sys
import base64
import urllib.request
import http.cookiejar
from time import sleep

import yaml
import pendulum
from pypdf import PdfReader
from selenium import webdriver
from selenium.webdriver.common.by import By

# Find pdf header :
# pdftotext -W 941 -H 50 2015-02-13_9.pdf -
# we can then use PDFTK to reconstruct the pdf
# maybe a nice quick and dirty ruby/bash script would do the trick


class MissingPagesError(RuntimeError):
    pass


class KazetennScraper:
    DEFAULT_EDITION = "nord-finistere"

    def __init__(self):
        options = webdriver.FirefoxOptions()
        options.add_argument("--devtools")

        profile = webdriver.FirefoxProfile()
        profile.set_preference("devtools.toolbox.selectedTool", "netmonitor")
        profile.set_preference("devtools.netmonitor.persistlog", False)
        options.profile = profile

        browser = webdriver.Firefox(options=options)
        browser.install_addon("firefox_extensions/har_export_trigger-0.6.2resigned1.xpi")
        browser.install_addon("firefox_extensions/uBlock0_1.60.0.firefox.signed.xpi")
        browser.implicitly_wait(10)

        browser.get("https://www.ouest-france.fr")
        browser.find_element(By.CSS_SELECTOR, "#didomi-notice-agree-button").click()
        self.browser = browser

    def __del__(self):
        self.browser.close()
        self.browser.quit()

    def download_journal(self, date, dl_path=None, edition=None):
        self.seen_pages = set()
        self.pages_num = 0
        self.dl_pages = []
        self.dl_path = dl_path or './tmp'
        edition = edition or self.DEFAULT_EDITION
        self.browser.get(f"https://www.ouest-france.fr/premium/journal/journal-ouest-france/{date}/?edition={edition}")
        self.browser.find_element(By.CSS_SELECTOR, "section.bp-zone-lecture a img").click()
        self.number_of_pages = self.get_number_of_pages()
        sleep(1)
        self.download_new_pages()
        for k in range(0, self.number_of_pages // 2):
            if k != 0 and self.spread_is_single_page():
                self.dl_pages.append("double_spread")
            self.change_page()
            self.download_new_pages()
        self.check_pages_number()

    def download_new_pages(self):
        # see https://defgsus.github.io/blog/2021/03/07/selenium-firefox-har-extract.html
        har_data = self.browser.execute_async_script("HAR.triggerExport().then(arguments[0]);")
        urls = [entry["request"]["url"] for entry in har_data["entries"]]
        page_urls = set([url for url in urls if url.startswith("https://wsjournal.ouest-france.fr/bdc/page")])
        new_pages = page_urls - self.seen_pages
        self.seen_pages |= page_urls
        for page in new_pages:
            page_number = len(self.dl_pages)
            filename = f"{self.dl_path}/{page_number:02}.pdf"
            with open(filename, "wb") as out_file:
                for entry in [entry for entry in har_data["entries"] if entry["request"]["url"] == page]:
                    try:
                        text_content = entry["response"]["content"]["text"]
                    except KeyError:
                        text_content = ""
                    max_chunk_size = 1048576
                    try:
                        for x in range(0, len(text_content), max_chunk_size):
                            chunk = text_content[x : x + max_chunk_size]
                            out_file.write(base64.b64decode(chunk))
                    except ValueError:
                        pass
            try:
                PdfReader(filename, strict=True).get_page(0)
            except:
                self.download_page(page, filename)
            try:
                PdfReader(filename, strict=True).get_page(0)
            except Exception as e:
                if repr(e) == "PdfReadError('startxref not found')":
                    # This error does not seem to impact PDF quality
                    continue
                raise MissingPagesError(f"failed to download correctly page {filename}")
            self.dl_pages.append(filename)

    def change_page(self):
        iframe = self.browser.find_element(By.CSS_SELECTOR, "div.parution-reader-popin > div.popin-content > iframe")
        self.browser.switch_to.frame(iframe)
        self.browser.find_element(By.CSS_SELECTOR, "button.right").click()
        # Wait for page loading
        timeout = 0
        while timeout < 10:
            loaders = self.browser.find_elements(By.CSS_SELECTOR, "div.loader")
            if set([loader.get_attribute("style") for loader in loaders]) == set(["display: none;"]):
                break
            else:
                timeout += 1
                sleep(1)
        self.browser.switch_to.default_content()

    def spread_is_single_page(self):
        iframe = self.browser.find_element(By.CSS_SELECTOR, "div.parution-reader-popin > div.popin-content > iframe")
        self.browser.switch_to.frame(iframe)
        number_of_pages_in_spread = len(self.browser.find_elements(By.CSS_SELECTOR, "canvas"))
        self.browser.switch_to.default_content()
        return number_of_pages_in_spread == 1

    def get_number_of_pages(self):
        iframe = self.browser.find_element(By.CSS_SELECTOR, "div.parution-reader-popin > div.popin-content > iframe")
        self.browser.switch_to.frame(iframe)
        number_of_pages = int(self.browser.find_element(By.CSS_SELECTOR, "span.page-selector-container > span").text)
        self.browser.switch_to.default_content()
        return number_of_pages

    def add_cookie(self, name, cookie):
        self.browser.add_cookie({"name": name, "value": cookie, "domain": ".ouest-france.fr"})
        if name == "datadome":
            self.cookie = "datadome=" + cookie

    def download_page(self, url, filename):
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        urllib.request.install_opener(opener)

        req = urllib.request.Request(url)
        req.add_header("Cookie", self.cookie)

        with urllib.request.urlopen(req) as response:
            with open(filename, "wb") as out_file:
                while True:
                    try:
                        out_file.write(response.read())
                    except http.client.IncompleteRead as icread:
                        out_file.write(icread.partial)
                        continue
                    else:
                        break

    def check_pages_number(self):
        n_wanted = self.number_of_pages
        n_real = len(self.dl_pages)
        if n_wanted != n_real:
            raise MissingPagesError(
                f"Issue with {self.dl_path}, since journal has {n_wanted} pages and we save {n_real} pages."
            )


if __name__ == "__main__":
    edition = KazetennScraper.DEFAULT_EDITION

    config = yaml.safe_load(open("config.yaml"))
    if "edition" in config:
        edition = config["edition"]

    date = pendulum.parse(sys.argv[1]).to_date_string()
    if len(sys.argv) > 2:
        edition = sys.argv[2]

    scraper = KazetennScraper()
    for name, value in config["cookies"].items():
        scraper.add_cookie(name, value)
    scraper.download_journal(date, edition=edition)
    del scraper
    sleep(1)
