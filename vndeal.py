import os
import re
import requests
import pprint
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import sqlite3

load_dotenv()

ITAD_API_KEY = os.getenv("ITAD_API_KEY")

ITAD_URL = "https://api.isthereanydeal.com"

VN_URL = "https://api.vndb.org/kana/vn"

DB_PATH = "vn.db"

STEAM_SHOPID = 61 # Shop ID de Steam sur ITAD


# VNDB.org API v2 (Kana) =============================================

def regex_steam_appid(extlinks):
    steam_link = 'store.steampowered.com'
    for extlink in extlinks:
        vendorlink = extlink['url']
        if re.search(steam_link, vendorlink):
            correspondance = re.search(r"https://store\.steampowered\.com/app/(\d+)/", vendorlink)
            if correspondance:
                return correspondance.group(1)
    return None

def vnid_to_steamid(vnid):
    RELEASE_URL = "https://api.vndb.org/kana/release"
    rbody = {
    "filters": [
        "and",
        ['vn', '=', ['id', '=', vnid]],  
        ['extlink', '=', 'steam'],
        ['has_ero', '!=', 1]
    ],
    "fields": "extlinks.url",
    "results": 1
    }
    response = requests.post(RELEASE_URL, json=rbody, timeout=10)
    # print("Code HTTP (Release):", response.status_code)
    if response.status_code != 200:
        print(response.text)
        return None
    else:
        data = response.json()
        extlinks = data['results'][0]['extlinks']
        steamid = regex_steam_appid(extlinks)
        return steamid


def load_n_vns(nb_vn: int) -> list[dict]:
    vn_list = []
    #SELECT id, title, rating, votecount, image.sexual, extlink
    #FROM vn 
    #WHERE rating >= 75 AND votecount >= 1000 AND existe au moins un release SFW et un release Steam.  
    vbody = {
        "filters": [
            "and",          # These are represented as JSON arrays where the first element is either "and" or "or", followed by two or more other predicates.
            ["rating", ">=", 65],       # a ajuster ou rendre ajustable par user 
            ["votecount", ">=", 100],
            ["release", "=", ['and', ["minage", "<", 18],  ["extlink", "=", "steam"]], # Si vndb peut parcourir chaque release et verifier l'age recquis, il pourrait aussi renvoyer les liens externes ?
            # vndb filtre les vn qu'ils renvoie de son cote en regardant les releases mais ne peut pas renvoyer les infos trouves dans les releases. Tout simplement car y a pas dans fields.
        ]
        ],
        
        "fields": "id, title, rating, votecount",
        "sort": "votecount",           #SORT BY votecount, ou un sort par rating possible mais sors vn a peu de votes. solution : ajuster les filtres au dessus ?
        "reverse": True, # Set to true to sort in descending order. -Kana
        "results": nb_vn,  # nb de vn a renvoyer
    }

    response = requests.post(VN_URL, json=vbody, timeout=10)
    # print("Code HTTP :", response.status_code)
    if response.status_code != 200:
        print(response.text)
        return None
    else:
        data = response.json()
        for visual_novel in data['results']:
            vn_list.append({
                "vndb_id": visual_novel['id'],
                "vndb_title": visual_novel["title"],
                "vndb_rating": visual_novel["rating"],
                "vndb_votecount": visual_novel["votecount"],
                "steam_id": None,
                "itad_id": None,
                "price": None,
                "price_history": None,
                }
            )
    return vn_list

# IsThereAnyDeal API (2.11.0) =============================================

def steam_to_itad_id(steam_id):
    LOOKUP_URL = f"{ITAD_URL}/lookup/id/shop/{STEAM_SHOPID}/v1"
    payload = [f"app/{steam_id}"]
    response = requests.post(
        LOOKUP_URL,
        params={"key": ITAD_API_KEY},
        json=payload,
        timeout=10,
    )
    if response.status_code != 200:
        print(response.text)
        return None
    else:
        data = response.json()
        return data.get(f"app/{steam_id}")

def itad_price(itad_id, country='FR'):
    LOOKUP_URL = f"{ITAD_URL}/games/prices/v3"
    payload = [itad_id]
    response = requests.post(
        LOOKUP_URL,
        params={"key": ITAD_API_KEY,
                "country": country,
                "shops": STEAM_SHOPID},
        json=payload,
        timeout=10,
    )
    if response.status_code != 200:
        print(response.text)
        return None
    else:
        data = response.json()
        dict_price = {
            "itad_id": itad_id,
            "country": country,
            "regular": data[0]['deals'][0]['regular']['amountInt'],
            "price": data[0]['deals'][0]['price']['amountInt'],
            "cut": data[0]['deals'][0]['cut'],
            "currency": data[0]['deals'][0]['price']['currency'],
            "timestamp": data[0]['deals'][0]['timestamp']
        }
        return dict_price

def price_history(itad_id, country='FR'):           # a parametrer pour avoir historique tres anciens sans se faire bloquer
    LOOKUP_URL = f"{ITAD_URL}/games/history/v2"
    response = requests.get(
        LOOKUP_URL,
        params={"key": ITAD_API_KEY,
                "id": itad_id,
                "country": country,
                "shops": STEAM_SHOPID,
                "since": "2011-01-01T00:00:00Z"},   
        timeout=10,
    )
    if response.status_code != 200:
        print(response.text)
        return None
    else:
        data = response.json()
        ld_price_history:list[dict] = []
        for price_log in data:
            ld_price_history.append({
                "itad_id": itad_id,
                "country": country,
                "regular": price_log['deal']['regular']['amountInt'],
                "price": price_log['deal']['price']['amountInt'],
                "cut": price_log['deal']['cut'],
                "currency": price_log['deal']['price']['currency'],
                "timestamp": price_log['timestamp']
            }
            )
        return ld_price_history

# SQLite3 =============================================================

def get_connection(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(conn):
    sql_vn = """CREATE TABLE IF NOT EXISTS vn(
        vndb_id TEXT PRIMARY KEY,
        steam_id TEXT,
        itad_id TEXT,
        vndb_title TEXT NOT NULL,
        vndb_rating REAL,
        vndb_votecount INT,
        updated_at TEXT
    )"""
    
    sql_price_history = """CREATE TABLE IF NOT EXISTS price_history(
        itad_id TEXT NOT NULL,
        country TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        price INT,
        regular INT,
        cut INT,
        currency TEXT,
        PRIMARY KEY(itad_id, country, timestamp)
    )"""

    conn.execute(sql_vn)
    conn.execute(sql_price_history)
    conn.commit()

def save_vn(conn, vn):
    current_time = (datetime.now(timezone.utc).isoformat())
    sql = """INSERT INTO vn (vndb_id, steam_id, itad_id, vndb_title, vndb_votecount, vndb_rating, updated_at)
             VALUES(:vndb_id, :steam_id, :itad_id, :vndb_title, :vndb_votecount, :vndb_rating, :updated_at)
             ON CONFLICT(vndb_id) DO UPDATE SET
                itad_id = excluded.itad_id,
                vndb_rating = excluded.vndb_rating,
                vndb_votecount = excluded.vndb_votecount,
                updated_at = excluded.updated_at"""
    conn.execute(sql, {**vn, "updated_at": current_time})
    conn.commit()

def save_price_history(conn, rows):
    sql = """INSERT OR IGNORE INTO price_history (itad_id, country, timestamp, price, regular, cut, currency)
         VALUES (:itad_id, :country, :timestamp, :price, :regular, :cut, :currency)"""
    conn.executemany(sql, rows)
    conn.commit()

def get_vn(conn, vndb_id) -> dict|None:
    sql = """SELECT * FROM vn WHERE vndb_id = ?"""
    cur = conn.execute(sql, (vndb_id,))
    row = cur.fetchone()
    if row:
        return dict(row)
    else:
        return None

def get_price_history(conn, itad_id, country)->list:
    sql = """SELECT * FROM price_history WHERE itad_id = ? AND country = ?
             ORDER BY timestamp ASC"""
    cur = conn.execute(sql, (itad_id, country,))
    rows = cur.fetchall()
    return [dict(row) for row in rows]

# def get_sales(conn, itad_id, country):
#     sql = """SELECT * FROM price_history WHERE itad_id = ? AND country = ? AND cut > 0
#              ORDER BY timestamp DESC"""
#     cur = conn.execute(sql, (itad_id, country,))
#     rows = cur.fetchall()
#     return [dict(row) for row in rows]

def is_fresh(conn, vndb_id, max_time: timedelta) -> bool:
    sql = """SELECT updated_at FROM vn WHERE vndb_id = ?"""
    cur = conn.execute(sql, (vndb_id,))
    row = cur.fetchone()
    if row is None or row['updated_at'] is None:
        return False
    else:
        current_time = datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(row['updated_at'])
        return current_time - updated_at < max_time

def refresh_vns(conn, nb_vn, max_time:timedelta, country="FR"):
    init_db(conn)
    l_dict_vn = load_n_vns(nb_vn) 
    for dict_vn in l_dict_vn:
        if not is_fresh(conn, dict_vn['vndb_id'], max_time):
            dict_vn["steam_id"] = vnid_to_steamid(dict_vn['vndb_id'])
            dict_vn["itad_id"] = steam_to_itad_id(dict_vn["steam_id"])
            dict_vn["price"] = itad_price(dict_vn["itad_id"], country)
            dict_vn["price_history"] = price_history(dict_vn["itad_id"], country)
            save_vn(conn, dict_vn)
            save_price_history(conn, dict_vn["price_history"])

# prediction prochaine date de solde par mediane

def sales_gaps(history:list[dict])->list[timedelta]:    # en param: history est la liste de dict renvoye par requete SQL de la fonction get_price_history
    l_gap_durations = []
    gap_start = None
    in_sale:bool = False
    for log in history:   # 
        timestamp:datetime = datetime.fromisoformat(log["timestamp"]).astimezone(timezone.utc)
        if gap_start is None:
            if log["cut"] == 0:
                gap_start = timestamp
                in_sale = False
        else:
            if log["cut"] == 0 and in_sale:
                gap_start:datetime = timestamp
                in_sale = False
            elif log["cut"] > 0 and not in_sale:
                gap_end:datetime = timestamp
                gap_duration:timedelta = gap_end - gap_start
                l_gap_durations.append(gap_duration)
                in_sale = True
    return l_gap_durations

def gap_median(l_gaps:list[timedelta])->timedelta|None:
    i_median:int = len(l_gaps) // 2
    return sorted(l_gaps)[i_median]

def estimate_next_sale(history:list[dict], seuil:int=10)->datetime|None: # None si pas assez d'entrees, eg: vn gratuit
    l_gaps = sales_gaps(history)
    if len(l_gaps) < seuil:
        return None
    estimated_gap_duration = gap_median(l_gaps)
    latest_gap_start:int = history[-1]["timestamp"]
    next_sale_date:datetime = datetime.fromisoformat(latest_gap_start) + estimated_gap_duration
    return next_sale_date.astimezone(timezone.utc)