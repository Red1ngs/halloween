CONFIG_FILE = "data/config.json"
LAST_READED = "data/last_readed.txt"
LOG_FILE = "script.log"

DB_PATH = "data/manga.db"
DB_URL = f"sqlite:///{DB_PATH}"
CHAPTERS_FILE = "data/manga.json"

BASE_URL = "https://mangabuff.ru"
COOKIE_TTL = 28_800
ADD_HISTORY_PATH = "/addHistory?r=702"
TAKE_CANDY_PATH = "/halloween/takeCandy"
DELAY = 60.0
TARGET_COUNT = 10
SCRAPER_MANGA_PER_PAGE = 30
BATCH_SIZE = 2
MODE = "card" # "candy" or "card"
PARAMS = {
    "type_id[0]": "3",
    "tags[0]": "7702",
    "status_id[0]": "1",
    "status_id[1]": "2",
    "status_id[2]": "3",
    "rating[0]": "9",
    "year[0]": "2022",
    "year[1]": "2021",
    "year[2]": "2020",
    "year[3]": "2019",
    "year[4]": "2018",
    "chapters[0]": "100",
    "chapters[1]": "200",
    "without_genres[0]": "7",
    "without_genres[1]": "21",
    "without_genres[2]": "28",
    "without_genres[3]": "38"
    }
