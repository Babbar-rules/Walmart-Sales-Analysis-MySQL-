# Twice-weekly job search run (Wed & Sat)

Run from this folder. Every step uses only official company career pages (company-hosted Greenhouse /
Lever / Ashby / Workday / SmartRecruiters boards, amazon.jobs, Microsoft Careers) – never aggregators.

1. `pip install -q openpyxl` then `python3 fetch_jobs.py`
2. `python3 shortlist.py` – drops every job already in `seen_jobs.json` (already listed or already reviewed),
   so nothing is ever re-added.
3. Read `data/shortlist_review.txt` and `profile.md`. For each NEW candidate decide if it truly fits:
   minimum required experience ≤ 2 yrs (read the requirement text, not just the number), India/remote-India,
   and strong overlap with the profile. Write `data/selected.json`:
   `[{"id": 3, "company": "Acme", "location": "Bengaluru", "mode": "Hybrid",
      "experience": "1–3 yrs", "score": 88, "description": "<1–2 sentence role summary>",
      "why": "<why it matches the resume>"}]`
   Only include roles scoring ≥ 65. An empty list is fine if nothing new fits.
4. `python3 update_sheet.py` – verifies each link (HTTP 200 + posting live), appends only verified new jobs to
   `../Harpreet_Job_Matches.xlsx` with today's date, marks closed existing jobs, updates `seen_jobs.json`.
5. Commit `../Harpreet_Job_Matches.xlsx`, `seen_jobs.json`, `sources.json` (data/ is git-ignored) and push to
   the `claude/eager-maxwell-rwqja2` branch.
