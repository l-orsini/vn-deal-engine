import os
import re
import requests
import pprint
from dotenv import load_dotenv

load_dotenv()

ITAD_API_KEY = os.getenv("ITAD_API_KEY")

ITAD_URL = "https://api.isthereanydeal.com"

VN_URL = "https://api.vndb.org/kana/vn"



# VNDB.org API v2 (Kana) =============================================
    
def load_n_vns(dictionnaire_vn, nb_vn):
    #SELECT id, title, rating, votecount, image.sexual, extlink
    #FROM vn 
    #WHERE rating >= 75 AND votecount >= 1000 AND existe au moins un release SFW et un release Steam. pourrait renvoyer un VN avec lien Steam mais pas SFW et vice versa ?  
    vbody = {
        "filters": [
            "and",          # These are represented as JSON arrays where the first element is either "and" or "or", followed by two or more other predicates.
            ["rating", ">=", 65],       # a ajuster
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
            dictionnaire_vn[visual_novel['id']] = {
                "vndb_id": visual_novel['id'],
                "vndb_title": visual_novel["title"],
                "vndb_rating": visual_novel["rating"],
                "vndb_votecount": visual_novel["votecount"],
                "steam_id": None,
                "itad_id": None,
                "price": None,
                "price_history": None,
                "recommendations": [],
}


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


def regex_steam_appid(extlinks):
    steam_link = 'store.steampowered.com'
    for extlink in extlinks:
        vendorlink = extlink['url']
        if re.search(steam_link, vendorlink):
            correspondance = re.search(r"https://store\.steampowered\.com/app/(\d+)/", vendorlink)
            if correspondance:
                return correspondance.group(1)
    return None



# IsThereAnyDeal API (2.11.0) =============================================

def steam_to_itad_id(steam_id):
    LOOKUP_URL = f"{ITAD_URL}/lookup/id/shop/{61}/v1" #61 est le shop ID de steam sur ITAD
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


def itad_price(itad_id, country='US'):
    LOOKUP_URL = f"{ITAD_URL}/games/prices/v3"
    payload = [itad_id]
    response = requests.post(
        LOOKUP_URL,
        params={"key": ITAD_API_KEY,
                "country": country,
                "shops": 61},
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

def price_history(itad_id, country='US'):           # a parametrer pour avoir historique tres anciens sans se faire bloquer
    LOOKUP_URL = f"{ITAD_URL}/games/history/v2"
    response = requests.get(
        LOOKUP_URL,
        params={"key": ITAD_API_KEY,
                "id": itad_id,
                "country": country,
                "shops": 61},
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


# Main temporaire

# vn_dict = { 'id vndb': {dict avec caracteristiques}, 'v203': {vndbid:'v203', titre: ..., avis: ..., prix: ...}}
# vn_dict = {}
# load_n_vns(vn_dict, 1)
# for visual_novel_id in vn_dict:
#     visunal_novel_steam_id = vnid_to_steamid(visual_novel_id)
#     vn_dict[visual_novel_id]['steam_id'] = visunal_novel_steam_id
#     vn_dict[visual_novel_id]['itad_id'] = steam_to_itad_id(visunal_novel_steam_id)
#     vn_dict[visual_novel_id]['price'] = itad_price(vn_dict[visual_novel_id]['itad_id'])

# pprint.pprint(vn_dict)

pprint.pprint(price_history(steam_to_itad_id('1113560')))