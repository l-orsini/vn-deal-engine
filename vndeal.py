import re
import requests

URL = "https://api.vndb.org/kana/vn"


def get_steam_appid(extlinks):
    for link in extlinks or []:
        match = re.search(r"store\.steampowered\.com/app/(\d+)", link.get("url", ""))
        if match:
            return int(match.group(1))
    return None

#SELECT id, title, rating, votecount, image.sexual, extlink
#FROM vn 
#WHERE rating >= 75 AND votecount >= 1000 AND existe au moins un release SFW et un release Steam. pourrait renvoyer un VN avec lien Steam mais pas SFW et vice versa ?  
body = {
    "filters": [
        "and",
        ["rating", ">=", 65],       # a ajuster
        ["votecount", ">=", 100],
        ["release", "=", ["minage", "<", 18]], # Si vndb peut parcourir chaque release et verifier l'age recquis, il pourrait aussi renvoyer les liens externes ?
        ["release", "=", ["extlink", "=", "steam"]] # vndb filtre les vn qu'ils renvoie de son cote en regardant les releases mais ne peut pas renvoyer les infos trouves dans les releases. Tout simplement car y a pas dans fields.
    ],
    "fields": "id, title, rating, votecount, image.sexual, extlinks{name,url,label}",
    "sort": "votecount",           #SORT BY votecount, ou un sort par rating possible mais sors vn a peu de votes. solution : ajuster les filtres au dessus ?
    "reverse": True,
    "results": 30,
}

response = requests.post(URL, json=body, timeout=10)
print("Code HTTP :", response.status_code)

if response.status_code != 200:
    print(response.text)
else:
    data = response.json()
    for vn in data["results"]:
        image = vn.get("image")                      
        if not image or (image.get("sexual") or 0) > 0:  
            continue
        appid = get_steam_appid(vn.get("extlinks"))
        print(vn["title"], "|", vn["rating"], "|", appid)


assert get_steam_appid([]) is None
assert get_steam_appid(None) is None
assert get_steam_appid([{"url": "https://store.steampowered.com/app/412830"}]) == 412830
assert get_steam_appid([{"url": "https://www.wikidata.org/wiki/Q1"}]) is None
print("get_steam_appid : OK")