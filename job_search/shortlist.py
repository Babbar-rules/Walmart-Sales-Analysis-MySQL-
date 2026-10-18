"""Step 2: filter data/jobs.json down to India/remote AI roles needing <=2 yrs that are NOT already in the sheet.

Writes data/shortlist.json and data/shortlist_review.txt (experience snippets for Claude to review).
Jobs already listed (seen_jobs.json) are skipped so they are never re-added.
"""
import concurrent.futures as cf, html, json, os, re, urllib.request
from fetch_jobs import DATA, HERE, get, strip

IND = r"India|Bengaluru|Bangalore|Mumbai|Pune|Hyderabad|Gurgaon|Gurugram|Delhi|Noida|Chennai|Kolkata|Ahmedabad|Jaipur|Indore|Kochi"
TITLE = (r"\bAI\b|\bML\b|machine learning|gen ?ai|generative|\bLLM|applied (ai|ml|scien)|data scien|agent|\bNLP\b|forward deployed|"
         r"deployed engineer|solutions? engineer|research engineer|applied engineer|member of technical staff|prompt|founding engineer|intelligence|deep learning")
EXCLUDE = (r"senior|\bsr\.?\b|staff|principal|lead\b|manager|director|head\b|\bVP\b|architect|intern\b|internship|sales|account exec|recruit|"
           r"counsel|legal|marketing|designer|\bIII\b|\bIV\b|chief|executive|partner|finance|specialist|onboarding|analyst|data associate|associate ii")


DS_ML = r"data scien|applied scien|machine learning|\bML\b|research"
AI_FOCUS = r"\bAI\b|gen ?ai|generative|\bLLM|agent|forward deployed|deployed engineer"
LLM_DESC = r"\bLLMs?\b|large language|generative ai|genai|agentic|\bagents?\b|\bRAG\b|retrieval.augmented|prompt"


def ai_focused(j):
    """Keep data-science / ML / scientist titles only when the work is clearly about LLMs or agents."""
    if re.search(AI_FOCUS, j["title"], re.I) or not re.search(DS_ML, j["title"], re.I): return True
    return len(re.findall(LLM_DESC, j["desc"], re.I)) >= 3


def region(loc):
    if re.search(IND, loc, re.I) or re.search(r"\bIND?\b", loc): return "India"
    if re.search(r"remote", loc, re.I) and re.search(r"global|worldwide|anywhere|APAC|Asia", loc, re.I): return "Remote (Global/APAC)"
    if re.fullmatch(r"\s*(remote|distributed)(\s*remote)?\s*", loc, re.I): return "Remote"
    return None


def enrich(j):
    """Fill in descriptions for sources whose list API omits them."""
    if j["desc"]: return j
    if j["source"] == "smartrecruiters":
        d = get(f"https://api.smartrecruiters.com/v1/companies/{j['slug']}/postings/{j['sr_id']}") or {}
        j["desc"] = strip(" ".join((v or {}).get("text", "") for v in (d.get("jobAd", {}).get("sections") or {}).values()))
        j["url"] = d.get("postingUrl") or j["url"]
    elif j["source"] == "workday":
        d = (get(j["wd_api"]) or {}).get("jobPostingInfo") or {}
        j["desc"] = strip(d.get("jobDescription"))
        j["loc"] = " ".join([d.get("location", "") or j["loc"]] + (d.get("additionalLocations") or []))
        j["url"] = d.get("externalUrl") or j["url"]
    elif j["source"] == "microsoft":
        d = get(f"https://apply.careers.microsoft.com/api/pcsx/position_details?position_id={j['ms_id']}&domain=microsoft.com&hl=en") or {}
        j["desc"] = strip((d.get("data") or {}).get("jobDescription"))
    return j


def years(t):
    return [(int(a), int(b) if b else None) for a, b in
            re.findall(r"(\d{1,2})\s*(?:\+|-|–|to)?\s*(\d{1,2})?\s*\+?\s*(?:years|yrs)", t, re.I) if int(a) <= 15]


def main():
    jobs = json.load(open(os.path.join(DATA, "jobs.json")))
    seen = set(json.load(open(os.path.join(HERE, "seen_jobs.json"))))
    c = [j for j in jobs if region(j["loc"]) and re.search(TITLE, j["title"], re.I) and not re.search(EXCLUDE, j["title"], re.I)
         and j["url"] not in seen]
    with cf.ThreadPoolExecutor(12) as ex: c = list(ex.map(enrich, c))
    out, keys = [], set()
    for j in c:
        r = region(j["loc"])
        if not r or j["url"] in seen or not ai_focused(j): continue
        k = (j["company"].lower(), j["title"].strip().lower(), j["loc"][:20])
        if k in keys: continue  # duplicate posting of the same role/location
        keys.add(k)
        y = years(j["desc"]); j["region"] = r; j["min_years"] = min([a for a, _ in y], default=None)
        if j["min_years"] is not None and j["min_years"] > 2: continue  # clearly above the 2-year cap
        out.append(j)
    for i, j in enumerate(out): j["id"] = i
    json.dump(out, open(os.path.join(DATA, "shortlist.json"), "w"), indent=1)
    with open(os.path.join(DATA, "shortlist_review.txt"), "w") as f:
        for j in out:
            d = re.sub(r"\s+", " ", j["desc"])
            ctx = [d[max(0, m.start() - 140):m.end() + 100] for m in
                   re.finditer(r"\d{1,2}\s*(?:\+|-|–|to)?\s*\d{0,2}\s*\+?\s*(?:years|yrs)|experience|new grad|early.career|junior", d, re.I)][:5]
            m = re.search(r"(what you.ll do|responsibilit|about the role|the role|you will|key job)", d, re.I)
            f.write(f"\n### id={j['id']} | {j['company']} | {j['title']} | {j['loc'][:70]} | min_years={j['min_years']}\n{j['url']}\n")
            f.write("ROLE: " + d[(m.start() if m else 0):][:600] + "\n")
            for x in ctx: f.write("  ~ " + x + "\n")
    print(f"{len(out)} NEW candidate roles (after removing {len(seen)} already-listed jobs) -> data/shortlist_review.txt")


if __name__ == "__main__":
    main()
