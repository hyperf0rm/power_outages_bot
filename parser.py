import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import logging

load_dotenv()


class Parser:

    def __init__(self):
        self.url = os.getenv("URL")
        self.headers = {
            "Accept": os.getenv("ACCEPT"),
            "User-Agent": os.getenv("USER_AGENT")
        }

    def parse_website(self):
        """
        Parses website and returns dict:
        { "Date 1": ["Addresses 1", "Addresses 2"], ...}
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()

            page = BeautifulSoup(response.text, "html.parser")
            ps = [p.get_text() for p in page.find_all("p")]

            outages = {}
            current_date = None
            current_places = []

            for text in ps:
                if not text:
                    continue

                if "текущего года" in text:
                    if current_date:
                        outages[current_date] = current_places

                    current_date = text
                    current_places = []

                else:
                    if current_date:
                        current_places.append(text.removesuffix(","))

            if current_date:
                outages[current_date] = current_places

            return outages

        except requests.exceptions.HTTPError as error:
            logging.error(f"HTTP Error: {error}")
            logging.error(f"Response content: {error.response.text}")
        except requests.exceptions.ConnectionError as error:
            logging.error(f"Connection Error: {error}")
        except requests.exceptions.Timeout as error:
            logging.error(f"Timeout Error: {error}")
        except requests.exceptions.RequestException as error:
            logging.error(f"An unexpected error occurred: {error}")
