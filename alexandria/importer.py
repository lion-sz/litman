import urllib3
import json

base_url = "https://api.crossref.org/works/"
doi = "10.1257/mac.20200320"


def load_doi(doi: str):
    req_url = base_url + doi
    res = urllib3.request("GET", req_url)
    if res.status != 200:
        return None

    parsed = json.loads(res.data.decode("utf-8"))["message"]
    parsed = parsed
    return Entry.parse_obj(parsed)
