# Free Coding Agent Radar

A ChatGPT-independent public-source lead finder. No paid API, no local LLM, no package installation beyond Python 3. The collector searches GitHub repository metadata, Hacker News, and public Reddit RSS where available. It preserves up to 500 discoveries, labels every automated result unverified, and exposes source failures. It does not execute found projects, certify pricing, or bypass access restrictions. The dashboard links to existing verified pricing directories for manual follow-up.

## Free cloud setup

1. Create a **new public GitHub repository** (results and source are public; don't add secrets or private information).
2. Upload all files including the `.github` folder. In Settings > Pages choose **GitHub Actions** as the source. Enable Actions if required.
3. In Actions > Scan radar > Run workflow, run the first scan. Open the Pages URL after deployment. The workflow then attempts a scan every three hours. Scheduled GitHub jobs can be delayed or paused; public standard runners and Pages are normally free.
4. Bookmark the Pages URL on your PC or phone. No ChatGPT login is required.

## Local use

Run `python scan.py`, then `python -m http.server 8000 --directory docs` from this folder. Open http://localhost:8000. Internet access is needed to scan. GitHub may rate-limit unauthenticated API calls; GitHub Actions supplies its own token. Reddit may block its RSS endpoint; this is shown in source health rather than silently treated as no results.

The dashboard is a discovery MVP, not a fully automated AI evaluator. Review the official provider pricing, licensing, limits and security before installing anything. Never treat a score or a repository description as proof of free access.

## Repository integrations

Radar reads public README data from API-mega-list, agentic-ai-apis and Awesome Free AI Coding, extracts relevant free-cost mentions, and links to the exact source lines. It also monitors public repository metadata from hyperresearch, rakazo, WeKnora and magpie, along with those directories. All directory claims remain unverified. No third-party code is executed and no provider accounts, API keys or paid services are necessary. The watchlist is for evaluating potential future integration, not a claim that these frameworks are installed.
