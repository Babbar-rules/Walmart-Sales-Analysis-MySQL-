"""Step 1: pull every opening from the official company career boards in sources.json.

Writes data/jobs.json (all jobs) and data/companies.json (per-company counts).
"""
import concurrent.futures as cf, html, json, os, re, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
SRC = json.load(open(os.path.join(HERE, "sources.json")))
UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}


def strip(h):
    h = html.unescape(h or ""); h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def get(u, body=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(u, data=json.dumps(body).encode() if body else None,
                                         headers={**UA, "Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def greenhouse(s):
    d = get(f"https://boards-api.greenhouse.io/v1/boards/{s}/jobs?content=true") or {}
    return [dict(company=j.get("company_name") or s, title=j["title"], loc=(j.get("location") or {}).get("name", ""),
                 url=j["absolute_url"], desc=strip(j.get("content"))) for j in d.get("jobs", [])]


def lever(s):
    d = get(f"https://api.lever.co/v0/postings/{s}?mode=json") or []
    out = []
    for j in d if isinstance(d, list) else []:
        c = j.get("categories", {})
        desc = " ".join([j.get("descriptionPlain", "")] + [l.get("text", "") + " " + strip(l.get("content", "")) for l in j.get("lists", [])] + [j.get("additionalPlain") or ""])
        out.append(dict(company=s, title=j["text"], loc=" | ".join(c.get("allLocations") or [c.get("location", "")]) + " " + (j.get("workplaceType") or ""),
                        url=j["hostedUrl"], desc=desc))
    return out


def ashby(s):
    d = get(f"https://api.ashbyhq.com/posting-api/job-board/{s}") or {}
    out = []
    for j in d.get("jobs", []):
        locs = [j.get("location", "")] + [x.get("location", "") for x in (j.get("secondaryLocations") or [])]
        a = (j.get("address") or {}).get("postalAddress") or {}
        out.append(dict(company=s, title=j["title"], loc=" | ".join(locs) + " " + (a.get("addressCountry") or "") + (" Remote" if j.get("isRemote") else ""),
                        url=j["jobUrl"], desc=j.get("descriptionPlain", "")))
    return out


def smartrecruiters(s):
    out, off = [], 0
    while off < 2000:
        d = get(f"https://api.smartrecruiters.com/v1/companies/{s}/postings?limit=100&offset={off}")
        if not d or not d.get("content"): break
        for j in d["content"]:
            l = j.get("location", {})
            out.append(dict(company=s, title=j["name"], loc=f"{l.get('city','')}, {l.get('country','')} {'Remote' if l.get('remote') else ''}",
                            url=f"https://jobs.smartrecruiters.com/{s}/{j['id']}", sr_id=j["id"], desc=""))
        off += 100
        if off >= d.get("totalFound", 0): break
    return out


def workday(t):
    ten, n, site = t
    base = f"https://{ten}.wd{n}.myworkdayjobs.com"
    seen = {}
    for q in ["generative AI", "machine learning", "LLM", "AI engineer", "data scientist", "agentic AI"]:
        d = get(f"{base}/wday/cxs/{ten}/{site}/jobs", {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q + " India"}) or {}
        for j in d.get("jobPostings", []):
            if "title" in j and "externalPath" in j:
                seen[j["externalPath"]] = dict(company=ten, title=j["title"], loc=j.get("locationsText", ""),
                                               url=f"{base}/{site}{j['externalPath']}", wd_api=f"{base}/wday/cxs/{ten}/{site}{j['externalPath']}", desc="")
    return list(seen.values())


def amazon():
    out, seen = [], set()
    for q in ["generative AI", "machine learning", "applied scientist", "LLM", "data scientist", "AI agent"]:
        d = get("https://www.amazon.jobs/en/search.json?" + urllib.parse.urlencode({"base_query": q, "loc_query": "India", "country": "IND", "result_limit": 100})) or {}
        for j in d.get("jobs", []):
            if j["id_icims"] in seen: continue
            seen.add(j["id_icims"])
            out.append(dict(company="Amazon", title=j["title"], loc=j.get("normalized_location", ""), url="https://www.amazon.jobs" + j["job_path"],
                            desc=strip(j.get("description")) + " BASIC QUALIFICATIONS " + strip(j.get("basic_qualifications")) + " PREFERRED " + strip(j.get("preferred_qualifications"))))
    return out


def microsoft():
    pos = {}
    for q in ["machine learning", "generative AI", "AI engineer", "applied scientist", "data scientist", "LLM", "software engineer AI"]:
        for st in range(0, 100, 10):
            d = get("https://apply.careers.microsoft.com/api/pcsx/search?" + urllib.parse.urlencode({"domain": "microsoft.com", "query": q, "location": "India", "start": st}))
            p = ((d or {}).get("data") or {}).get("positions") or []
            if not p: break
            for x in p: pos[x["id"]] = x
    return [dict(company="Microsoft", title=x["name"], loc="; ".join(x["locations"]), url="https://apply.careers.microsoft.com" + x["positionUrl"],
                 ms_id=x["id"], desc="") for x in pos.values()]


def main():
    tasks = [(a, s) for a in ("greenhouse", "lever", "ashby", "smartrecruiters") for s in SRC.get(a, [])]
    tasks += [("workday", tuple(t)) for t in SRC.get("workday", [])]
    tasks += [("amazon", None), ("microsoft", None)]
    fn = dict(greenhouse=greenhouse, lever=lever, ashby=ashby, smartrecruiters=smartrecruiters, workday=workday,
              amazon=lambda _: amazon(), microsoft=lambda _: microsoft())
    jobs, companies = [], []
    with cf.ThreadPoolExecutor(24) as ex:
        futs = {ex.submit(fn[a], s): (a, s) for a, s in tasks}
        for f in cf.as_completed(futs):
            a, s = futs[f]
            try: js = f.result()
            except Exception: js = []
            key = s if isinstance(s, str) else (s[0] if s else a)
            for j in js: j.update(source=a, slug=key)
            jobs += js
            companies.append(dict(source=a, slug=key, board=board_url(a, s), openings=len(js)))
    json.dump(jobs, open(os.path.join(DATA, "jobs.json"), "w"))
    json.dump(companies, open(os.path.join(DATA, "companies.json"), "w"), indent=1)
    print(f"{len(jobs)} openings from {sum(1 for c in companies if c['openings'])}/{len(companies)} boards")
    dead = [c["slug"] for c in companies if not c["openings"]]
    if dead: print("Boards returning 0 openings (check if moved):", ", ".join(dead))


def board_url(a, s):
    return {"greenhouse": f"https://job-boards.greenhouse.io/{s}", "lever": f"https://jobs.lever.co/{s}",
            "ashby": f"https://jobs.ashbyhq.com/{s}", "smartrecruiters": f"https://careers.smartrecruiters.com/{s}",
            "amazon": "https://www.amazon.jobs/en/search?base_query=machine+learning&loc_query=India",
            "microsoft": "https://apply.careers.microsoft.com/careers?query=machine+learning&location=India"}.get(a) or \
        (f"https://{s[0]}.wd{s[1]}.myworkdayjobs.com/{s[2]}" if a == "workday" else "")


if __name__ == "__main__":
    main()
