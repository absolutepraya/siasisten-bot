import requests as r
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class ScraperRequests:
    def __init__(self):
        self.client = r.Session()
        if not self.login():
            logger.error("Failed to log in. Scraper will not function.")
            raise Exception("Login failed.")

    def login(self):
        login_url = "https://siasisten.cs.ui.ac.id/login/"
        try:
            # Fetch the login page to get CSRF token
            response = self.client.get(login_url)
            response.raise_for_status()
            logger.info("Fetched login page successfully.")

            # Parse CSRF token
            soup = BeautifulSoup(response.content, "html.parser")
            csrf_token_input = soup.find("input", {"name": "csrfmiddlewaretoken"})
            if not csrf_token_input:
                logger.error("CSRF token not found on login page.")
                return False
            csrftoken = csrf_token_input.get("value")
            logger.info("CSRF token extracted.")

            # Prepare login payload
            username = os.getenv("SSO_USN")
            password = os.getenv("SSO_PASS")
            login_payload = {
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": csrftoken,
                "next": "",
            }

            headers = {
                "Referer": login_url,
                "User-Agent": "Mozilla/5.0 (compatible; SiAsistenBot/1.0)",
            }

            # Perform login
            login_response = self.client.post(
                login_url, data=login_payload, headers=headers
            )
            login_response.raise_for_status()
            logger.info("Login POST request successful.")

            # Verify login by checking if redirected away from login page
            if login_response.url == login_url:
                logger.error("Login failed. Check your credentials.")
                return False
            else:
                logger.info("Login successful.")
                return True

        except Exception as e:
            logger.exception(f"An error occurred during login: {e}")
            return False

    def get_lowongan(self):
        list_lowongan_url = "https://siasisten.cs.ui.ac.id/lowongan/listLowongan/"
        base_url = "https://siasisten.cs.ui.ac.id"

        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; SiAsistenBot/1.0)"}
            response = self.client.get(list_lowongan_url, headers=headers)
            response.raise_for_status()
            logger.info("Fetched lowongan list page successfully.")

            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.find_all("table")

            if not tables:
                logger.error("No <table> elements found on the page.")
                return []

            # Assuming the first table contains the lowongan list
            table = tables[0]
            rows = table.find_all("tr")

            if len(rows) <= 1:
                logger.warning("No data rows found in the table.")
                return []

            lowongan_list = []

            for row in rows[1:]:
                cols = row.find_all("td")
                if len(cols) < 9:
                    logger.warning("Skipping a row due to insufficient columns.")
                    continue

                # Extract job title
                title_cell = cols[1]
                # Use separator="\n" to handle <br> tags
                title = title_cell.get_text(separator="\n").strip()

                # Extract 'Daftar' link
                daftar_cell = cols[8]
                daftar_link_tag = daftar_cell.find("a", href=True)
                if daftar_link_tag:
                    daftar_link = base_url + daftar_link_tag["href"]
                else:
                    daftar_link = "Link not available"

                lowongan_entry = {"title": title, "daftar_link": daftar_link}

                lowongan_list.append(lowongan_entry)

            logger.info(f"Extracted {len(lowongan_list)} lowongan entries.")
            return lowongan_list

        except Exception as e:
            logger.exception(f"An error occurred while fetching lowongan: {e}")
            return []
