# Hotline.ua parser
Simple parser for hotline.ua made w/ Beautifulsoup, requests, pandas.
Gets needed items from certain category 
and stores data in the specified .csv file.
Also shows price changes if an item was previously parsed 
(prints price changes to console).

***

## Installation and usage

- clone the repo:
```
git clone https://github.com/Cerne13/hotline-ua-parser.git
```

- create venv if necessary
<br></br>

- install dependencies
```
pip install -r requirements.txt
```
- specify constants (see below)
<br></br>

- run the parse.py file

***

### Constants
**BASE_URL**: The first page of the category to be parsed.

**ITEMS_LIST**: Data file used to filter out needed items. Should contain
all the items you want to get data for (case sensitive) each on a new line.
Must be in the same directory with parse.py

**OUTPUT_FILE**: Filename of csv file where gathered data will be stored.
Will appear in the same directory with parse.py.
If you run the script again, the gathered data will be replaced with newly
scraped one.

***

