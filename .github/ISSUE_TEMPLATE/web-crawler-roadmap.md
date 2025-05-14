---
name: 🕷️ Web Crawler Dev Plan
about: Track the 10-week roadmap for building and publishing a Python-based web crawler
title: "[TRACKER] Web Crawler Development Roadmap"
labels: enhancement, project
assignees: swayamdani

---

## 📅 Weekly Tasks

- [ ] **Week 1 (June 17–23):** Learn HTTP basics & fetch pages using `http.client` or `requests`
- [ ] **Week 2 (June 24–30):** Extract links from raw HTML using regex or string parsing
- [ ] **Week 3 (July 1–7):** Normalize URLs and implement basic crawling with depth limit
- [ ] **Week 4 (July 8–14):** Add visited set, domain restriction, and basic logging
- [ ] **Week 5 (July 15–21):** Implement robots.txt parser and respect disallowed paths
- [ ] **Week 6 (July 22–28):** Add CLI options for depth, domain, output format
- [ ] **Week 7 (July 29–Aug 4):** Refactor code, split into modules, and write documentation
- [ ] **Week 8 (Aug 5–11):** Add `setup.py`, README, license, and prep for PyPI
- [ ] **Week 9 (Aug 12–18):** Write tests, finalize CLI, and publish to GitHub
- [ ] **Week 10 (Aug 19–25):** Upload to PyPI and announce project

---

## 🛡️ Repo Security Setup Checklist

- [ ] Enable branch protection rules (require PR reviews, no direct `main` pushes)
- [ ] Add `.gitignore` (for `__pycache__`, `.env`, etc.)
- [ ] Set up `LICENSE` (MIT recommended)
- [ ] Add `SECURITY.md` for responsible disclosure
- [ ] Set Dependabot alerts (GitHub Settings > Security > Enable alerts)
- [ ] Use `bandit` or `pylint` for security linting (CI)
- [ ] Restrict GitHub Actions to reviewed workflows only

---

## 📂 Suggested Repo Structure

```bash
webcrawler/
├── crawler/
│   ├── __init__.py
│   ├── core.py
│   ├── utils.py
├── tests/
│   └── test_core.py
├── cli.py
├── setup.py
├── README.md
├── LICENSE
├── .gitignore
└── SECURITY.md
```

