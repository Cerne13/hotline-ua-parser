import csv
import os.path
import random
from dataclasses import dataclass, astuple, fields
from urllib.parse import urljoin

import numpy as np
import pandas as pd

import requests
from bs4 import BeautifulSoup, Tag

BASE_URL = "https://hotline.ua/ua/computer/noutbuki-netbuki/33373/"
ITEMS_LIST = "items.txt"
OUTPUT_FILE = "laptops.csv"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 6.1; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.10; rv:75.0) Gecko/20100101 Firefox/75.0",
    "Mozilla/5.0 (X11; Linux; rv:74.0) Gecko/20100101 Firefox/74.0",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.4; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2225.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.24 (KHTML, like Gecko) Chrome/19.0.1055.1 Safari/535.24",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:47.0) Gecko/20100101 Firefox/47.0",
    "Mozilla/5.0 (Windows NT 6.1; U;WOW64; de;rv:11.0) Gecko Firefox/11.0",
    "Mozilla/5.0 (X11; ; Linux x86_64; rv:1.8.1.6) Gecko/20070802 Firefox",
    "Chrome/45.0.2454.85 Safari/537.36",
]


def get_random_header(user_agents: list) -> dict[str, str]:
    return {"User-Agent": random.choice(user_agents)}


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


def get_item_changes_info(laptop_obj, previously_got_list):
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


def parse_single_page(soup, needed_items, previously_got_list) -> [Laptop]:
    laptop_list = []
    laptop_divs = soup.select(".list-item")

    for laptop in laptop_divs:
        laptop_title = laptop.select_one(".list-item__title").text.strip()

        if laptop_title in needed_items:
            laptop_obj = parse_single_laptop(laptop)
            laptop_list.append(laptop_obj)

            get_item_changes_info(laptop_obj, previously_got_list)

    return laptop_list


def get_laptops_info() -> [Laptop]:
    page = requests.get(BASE_URL, headers=get_random_header(USER_AGENTS)).content
    soup = BeautifulSoup(page, "html.parser")

    needed_items = parse_data_file(ITEMS_LIST)
    previously_got_list = parse_previously_got_csv(OUTPUT_FILE)
    parsed_laptops = []

    parsed_laptops.extend(
        parse_single_page(soup, needed_items, previously_got_list)
    )

    # pagination
    next_page_disabled = soup.select_one("a.page--next.page--disabled")
    page = 2

    while next_page_disabled is None:
        print(f"Parsing: {BASE_URL}?p={page}")

        next_page = requests.get(
            urljoin(BASE_URL, f"?p={page}"),
            headers=get_random_header(USER_AGENTS)
        ).content

        soup = BeautifulSoup(next_page, "html.parser")
        next_page_disabled = soup.select_one("a.page--next.page--disabled")

        parsed_laptops.extend(parse_single_page(
            soup,
            needed_items,
            previously_got_list
        ))

        page += 1

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


def main():
    laptops = get_laptops_info()
    write_to_file(OUTPUT_FILE, laptops)


if __name__ == "__main__":
    main()
