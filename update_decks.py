import requests
import spacy
import time
import json
from datetime import datetime, timezone

nlp = spacy.load("en_core_web_sm")
#need to do this command: python -m spacy download en_core_web_sm

headers = {
    "User-Agent": "wikigen by rileycn"
}

wiki_url = "https://en.wikipedia.org/w/api.php"

reddit_cooldown = 0.5
wiki_cooldown = 0.5


def fetch_hot(subreddit, total):
    posts = []
    after = None
    while len(posts) < total:
        params = {
            "limit": 50,
            "after": after
        }
        reddit_url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        r = requests.get(reddit_url, headers=headers, params=params)
        if r.status_code != 200:
            break
        data = r.json()["data"]
        posts.extend(data["children"])
        after = data["after"]

        if not after:
            break
        time.sleep(reddit_cooldown)
    
    return posts

def titles_to_ids(titles):
    finalset = {}
    finallist = []
    for i in range(int(len(titles) / 50) + 1):
        kys = titles[(i * 50):min((i + 1) * 50, len(titles))]
        newparams = {
            "action": "query",
            "titles": "|".join(kys),
            "redirects": 1,
            "prop": "info|extracts",
            "exintro": 1,
            "explaintext": 1,
            "format": "json"
        }
        req = requests.get(wiki_url, headers=headers, params=newparams)
        if req.status_code != 200:
            break
        newdata = req.json()
        if "query" not in newdata:
            break
        pages = newdata["query"]["pages"]
        finalset.update({page["title"]: page["pageid"] for page in pages.values() if "pageid" in page})
        finallist.extend([page["pageid"] for page in pages.values() if "pageid" in page])
        time.sleep(wiki_cooldown)
    
    return finallist

def round_to_fifty(num):
    return int(round(num / 50) * 50)

def generate_b_deck(approx_amt=1000,search_amt=400):
    posts = []
    posts.extend(fetch_hot("popculture", round_to_fifty(search_amt)))
    posts.extend(fetch_hot("popculturechat", round_to_fifty(search_amt)))
    posts.extend(fetch_hot("all", round_to_fifty(search_amt)))
    titles = [p["data"]["title"] for p in posts]
    entities = dict()
    for title in titles:
        doc = nlp(title)
        for ent in doc.ents:
            if ent.label_ in {"PERSON", "ORG", "GPE", "WORK_OF_ART", "PRODUCT"}:
                if ent.text in entities:
                    entities[ent.text] += 1
                else:
                    entities[ent.text] = 1
    sorted_dict = dict(sorted(entities.items(), key=lambda item: item[1], reverse=True))
    return titles_to_ids(list(sorted_dict.keys())[:(approx_amt)])

def generate_c_deck(approx_amt=500):
    titles = []
    for i in range(int(approx_amt/50)):
        params = {
            "action": "query",
            "list": "mostviewed",
            "pvimoffset": i * 50,
            "format": "json",
            "pvimlimit": 50
        }
        req = requests.get(wiki_url, headers=headers, params=params)
        if req.status_code != 200:
            break
        data = req.json()
        banned = ["Special:", "Main Page", "Special:", "Wikipedia:", "List of", "Deaths in", "Portal"]
        for vl in data["query"]["mostviewed"]:
            preprocess = True
            for b in banned:
                if vl["title"].startswith(b):
                    preprocess = False
                    break
            if preprocess:
                titles.append(vl["title"])
        time.sleep(wiki_cooldown)
    return titles_to_ids(titles)

bdeck = generate_b_deck()
cdeck = generate_c_deck()
date = datetime.now(timezone.utc).strftime("%Y%m%d")

with open("result.json", "w") as f:
    json.dump({"date": date, "b_deck": bdeck, "c_deck": cdeck}, f)
    
with open(f"archive/{date}.json", "w") as f:
    json.dump({"date": date, "b_deck": bdeck, "c_deck": cdeck}, f)

