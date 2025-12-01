import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os

load_dotenv()


class Parser:
    url = os.getenv("URL")
    accept = os.getenv("ACCEPT")
    user_agent = os.getenv("USER_AGENT")
    headers = {
        "Accept": accept,
        "User-Agent": user_agent
    }

    def __init__(self, addresses):
        self.addresses = addresses

    def create_date_list(self, count, initial_value=None):
        return [initial_value] * count

    def create_places_dict(self, count, initial_value=None):
        return {f'date_{i}': initial_value for i in range(count)}

    def parse_website(self):
        response = requests.get(self.url, self.headers)
        page = BeautifulSoup(response.text, "html.parser")
        dates_count = page.get_text().count('текущего года')
        ps = page.find_all('p')
        dates = self.create_date_list(dates_count)
        places_dict = self.create_places_dict(dates_count)
        date_index = 0
        first_iteration = True
        places = []

        for p in ps:
            string = str(p.get_text())
            if 'текущего года' in string:
                if first_iteration is True:
                    dates[date_index] = string
                    first_iteration = False
                    continue
                places_dict[f'date_{date_index}'] = places
                date_index += 1
                dates[date_index] = string
                places = []
                continue
            places.append(string)
        places_dict[f'date_{date_index}'] = places

        results_list = []
        for i in range(dates_count):
            for value in places_dict.get(f'date_{i}'):
                for address in self.addresses:
                    if address in value:
                        results_list.append(f'{dates[i]}\n{value}')

        if not results_list:
            return 'Нет информации об отключении электроэнергии по вашему адресу в ближайшие дни'
        else:
            for i in range(len(results_list)):
                result = "\n".join(results_list)
                return result
