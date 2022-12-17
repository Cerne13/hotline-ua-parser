import csv
from dataclasses import dataclass, astuple, fields
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://hotline.ua/ua/computer/noutbuki-netbuki/33373/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}
NOTEBOOKS_LIST = 'items.txt'


@dataclass
class Notebook:
    title: str
    available: bool
    propositions_quantity: int | None
    main_price: int | None
    min_price: int | None
    max_price: int | None


def parse_data_file(filename) -> list:
    with open(filename) as data_file:
        df_list = data_file.read().splitlines()

    return df_list


def parse_single_notebook(notebook: [Tag]) -> Notebook:
    title = notebook.select_one(".list-item__title").text.strip()

    main_price = notebook.select_one(".price__value")
    main_price_value = (
        int(main_price.text.replace(u"\xa0", u""))
        if main_price else None
    )

    quantity_elem = notebook.find(
        "a", attrs={
            "data-eventaction": "Priceline",
            "class": "link link--black text-sm m_b-5"
        }
    )
    quantity = int(quantity_elem.text.strip().split("(")[-1][:-1]) if quantity_elem else None

    min_price = None
    max_price = None

    if quantity and quantity > 3:
        minmax_prices = notebook.select_one(".m_b-5 > .text-sm") \
            .text.replace(u"\xa0", u"").strip().split()
        if minmax_prices[-1] == 'грн':
            min_price = int(minmax_prices[0])
            max_price = int(minmax_prices[2])

    return Notebook(
        title=title,
        available=True if main_price else False,
        propositions_quantity=quantity,
        main_price=main_price_value,
        min_price=min_price,
        max_price=max_price,
    )


def filter_notebooks(parsed_notebooks, db_file):
    needed_notebooks_titles = parse_data_file(db_file)

    filtered_list = []

    for notebook in parsed_notebooks:
        if astuple(notebook)[0] in needed_notebooks_titles:
            filtered_list.append(notebook)

    return filtered_list


def get_notebooks_info() -> [Notebook]:
    page = requests.get(BASE_URL, headers=HEADERS).content
    soup = BeautifulSoup(page, "html.parser")

    all_notebook_divs = soup.select(".list-item")

    parsed_notebooks = [
        parse_single_notebook(notebook)
        for notebook in all_notebook_divs
    ]

    # pagination
    next_page_disabled = soup.select_one("a.page--next.page--disabled")
    page = 2

    while next_page_disabled is None:
        print(f"Parsing: {BASE_URL}?p={page}")

        next_page = requests.get(
            urljoin(BASE_URL, f"?p={page}"),
            headers=HEADERS
        ).content

        soup = BeautifulSoup(next_page, "html.parser")
        next_page_disabled = soup.select_one("a.page--next.page--disabled")

        # Just a test item to see if contents is got successfully
        list_item_test = soup.select_one(".list-item__info").name
        print(
            "Contents got successfully"
            if list_item_test is not None
            else "Request blocked. You should try different VPN."
        )

        page += 1

        all_notebook_divs = soup.select(".list-item")
        parsed_notebooks.extend([
            parse_single_notebook(notebook)
            for notebook in all_notebook_divs
        ])

    filtered_list = filter_notebooks(parsed_notebooks, NOTEBOOKS_LIST)

    return filtered_list


def write_to_file(output_csv_path: str) -> None:
    with open(
            output_csv_path,
            "w",
            encoding="utf-8",
            newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow([field.name for field in fields(Notebook)])
        writer.writerows([astuple(notebook) for notebook in get_notebooks_info()])


if __name__ == "__main__":
    write_to_file("notebooks.csv")
