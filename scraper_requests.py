import requests as r
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


class ScraperRequests:
    def __init__(self):
        self.client = r.session()
        self.login()

    def login(self):
        self.client.get("https://siasisten.cs.ui.ac.id/login/")
        if "csrftoken" in self.client.cookies:
            csrftoken = self.client.cookies["csrftoken"]

        username = os.getenv("SSO_USN")
        password = os.getenv("SSO_PASS")
        login_payload = dict(username=username, password=password,
                             csrfmiddlewaretoken=csrftoken, next="")

        self.client.post(
            "https://siasisten.cs.ui.ac.id/login/", data=login_payload)

    def get_lowongan(self):
        res = self.client.get(
            "https://siasisten.cs.ui.ac.id/lowongan/listLowongan/")

        soup = BeautifulSoup(res.content, "html.parser")

        texts = []

        newest = soup.find_all("table")[0]
        rows = newest.find_all("tr")

        for row in rows[1:]:
            cols = row.find_all("td")
            text = cols[1].get_text().strip().replace("  ", "\n")
            texts.append(text)

        return texts
