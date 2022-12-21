import csv
import os.path
from dataclasses import dataclass, astuple, fields
from urllib.parse import urljoin

import numpy as np
import pandas as pd

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://hotline.ua/ua/computer/noutbuki-netbuki/33373/"
ITEMS_LIST = "items.txt"
OUTPUT_FILE = "laptops.csv"

HEADERS = {'User-Agent': 'Mozilla/5.0'}


@dataclass
class Laptop:
    title: str
    available: bool
    propositions_quantity: int
    main_price: int
    min_price: int
    max_price: int


def parse_data_file(filename) -> list:
    with open(filename) as data_file:
        df_list = data_file.read().splitlines()

    return df_list


def parse_single_laptop(laptop: [Tag]) -> Laptop:
    title = laptop.select_one(".list-item__title").text.strip()

    main_price = laptop.select_one(".price__value")
    main_price_value = (
        int(main_price.text.replace(u"\xa0", u""))
        if main_price else 0
    )

    quantity_elem = laptop.find(
        "a", attrs={
            "data-eventaction": "Priceline",
            "class": "link link--black text-sm m_b-5"
        }
    )

    quantity = 0
    if quantity_elem:
        quantity = int(quantity_elem.text.strip().split("(")[-1][:-1])
    elif main_price:
        quantity = 1

    min_price = 0
    max_price = 0

    if quantity and quantity > 3:
        minmax_prices = laptop.select_one(".m_b-5 > .text-sm") \
            .text.replace(u"\xa0", u"").strip().split()
        if minmax_prices[-1] == 'грн':
            min_price = int(minmax_prices[0])
            max_price = int(minmax_prices[2])

    return Laptop(
        title=title,
        available=True if main_price else False,
        propositions_quantity=quantity,
        main_price=main_price_value,
        min_price=min_price,
        max_price=max_price,
    )


def parse_previously_got_csv(filename: str) -> list:
    laptop_list = []

    if os.path.isfile(filename) and os.stat(filename).st_size > 0:
        df = pd.read_csv(
            filename,
            header=0,
            usecols=["title", "main_price", "min_price", "max_price"]
        ).replace(np.nan, None)

        for i, row in df.iterrows():
            laptop_list.append([
                row["title"],
                row["main_price"],
                row["min_price"],
                row["max_price"],
            ])

    return laptop_list


def get_item_changes_info(laptop, previously_got_list):
    laptop_obj = parse_single_laptop(laptop)

    for item in previously_got_list:
        if item[0] == laptop_obj.title:
            print(f"{item[0]} was previously parsed.")

            if item[1] != laptop_obj.main_price:
                print(
                    f"Price has changed: {item[1]} -> "
                    f"{laptop_obj.main_price}"
                )

            if item[2] != laptop_obj.min_price:
                print(
                    f"Min price changed: {int(item[2])} -> "
                    f"{laptop_obj.min_price}"
                )

            if item[3] != laptop_obj.max_price:
                print(
                    f"Max price changed: {int(item[3])} -> "
                    f"{laptop_obj.max_price}"
                )
            print("\n")


def parse_single_page(laptop_divs, db_file, previously_got_list) -> [Laptop]:
    laptop_list = []

    for laptop in laptop_divs:
        laptop_title = laptop.select_one(".list-item__title").text.strip()

        if laptop_title in db_file:
            laptop_obj = parse_single_laptop(laptop)
            laptop_list.append(laptop_obj)

            get_item_changes_info(laptop, previously_got_list)

    return laptop_list


def test_page_content_got_successfully(soup: BeautifulSoup) -> None:
    list_item_test = soup.select_one(".list-item__info").name
    print(
        "Contents got successfully"
        if list_item_test is not None
        else "Request blocked. You should try different VPN."
    )


def get_laptops_info() -> [Laptop]:
    page = requests.get(BASE_URL, headers=HEADERS).content
    soup = BeautifulSoup(page, "html.parser")

    needed_items = parse_data_file(ITEMS_LIST)

    # TODO: replace w/actual list
    previously_got_list = parse_previously_got_csv("laptops1.csv")
    parsed_laptops = []

    all_laptop_divs = soup.select(".list-item")

    parsed_laptops.extend(parse_single_page(
        all_laptop_divs,
        needed_items,
        previously_got_list
    ))

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

        test_page_content_got_successfully(soup)

        page += 1

        all_laptop_divs = soup.select(".list-item")

        parsed_laptops.extend(parse_single_page(
            all_laptop_divs,
            needed_items,
            previously_got_list
        ))

        if len(parsed_laptops) == len(needed_items):
            break

    return parsed_laptops


def write_to_file(output_csv_path: str, laptops_list: [Laptop]) -> None:
    with open(
            output_csv_path,
            "w",
            encoding="utf-8",
            newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow([field.name for field in fields(Laptop)])
        writer.writerows([astuple(laptop) for laptop in laptops_list])


if __name__ == "__main__":
    laptops = get_laptops_info()
    write_to_file(OUTPUT_FILE, laptops)
