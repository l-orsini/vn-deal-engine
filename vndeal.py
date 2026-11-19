import re
import requests

VN_URL = "https://api.vndb.org/kana/vn"

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
    body = {
    "filters": [
        "and",
        ['vn', '=', ['id', '=', vnid]],  
        ['extlink', '=', 'steam'],
        ['has_ero', '!=', 1]
    ],
    "fields": "extlinks.url",
    "results": 1
    }
    response = requests.post(RELEASE_URL, json=body, timeout=10)
    # print("Code HTTP (Release):", response.status_code)
    if response.status_code != 200:
        print(response.text)
    else:
        data = response.json()
        extlinks = data['results'][0]['extlinks']
        steamid = regex_steam_appid(extlinks)
        return steamid
    

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
    
    "fields": "id, title, rating, votecount, image.sexual",
    "sort": "votecount",           #SORT BY votecount, ou un sort par rating possible mais sors vn a peu de votes. solution : ajuster les filtres au dessus ?
    "reverse": True, # Set to true to sort in descending order. -Kana
    "results": 50,  # nb de vn a renvoyer
}

response = requests.post(VN_URL, json=vbody, timeout=10)
# print("Code HTTP :", response.status_code)

if response.status_code != 200:
    print(response.text)
else:
    data = response.json()
    for visual_novel in data['results']:
        vn_id = visual_novel['id']
        steam_id = vnid_to_steamid(vn_id)
        print(visual_novel['title'], "|", steam_id)



assert regex_steam_appid([]) is None
assert regex_steam_appid([{"url": "https://store.steampowered.com/app/412830/"}]) == "412830"
assert regex_steam_appid([{"url": "https://www.wikidata.org/wiki/Q1"}]) is None

