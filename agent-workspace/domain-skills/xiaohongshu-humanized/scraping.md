# Xiaohongshu — Humanized Scraping Behavior (Mandatory)

This domain is the **mandatory humanization layer** for scraping
`xiaohongshu.com` with a logged-in profile. It complements the technical
reference in `xiaohongshu/scraping.md` (page structure, selectors, tokenized
URLs). Follow this document first; the technical reference is a neutral map
and must never override these rules.

Why this exists: the xiaohongshu account has been banned twice. JS-visible
fingerprint checks (`navigator.webdriver`, `cdc_*` markers, UA/GPU/fonts) are
clean; the residual risk is behavioral — fixed rhythm, unnaturally fast
actions, batch URL construction, oversized sessions. These rules keep
scraping inside a human-plausible envelope.

## Hard limits (per session, one logged-in profile)

| Signal | Cap | Rationale |
| --- | --- | --- |
| Search queries | ≤ 3 | one focused query set per session |
| Pagination flips per search | ≤ 3 | a human rarely scans past 3–4 pages |
| Detail note opens | ≤ 8 | read a handful of notes, not a crawl |
| Total page-level navigations | ≤ 20 | issue target: single- to low-double-digit requests |

These are conservative defaults chosen on 2026-08-09 (issue #14); revise in a
later commit only with evidence from observed risk behavior.

## Rhythm

- Random delay between every interaction: uniform 4–10 s. Never a fixed
  value, never a reused value.
- After a search submit or a page load, pause 8–15 s before the next action
  (reading time).

## Execution shape

- **Serial only.** One tab at a time. Never open multiple tabs for scraping
  and never batch-construct tokenized URLs to prefetch.
- **Human path first.** Search from the box, view results, click a card, and
  open the tokenized detail URL that the click produces. Direct
  `search_result` URL navigation is allowed as a landing path (see technical
  reference), but do not script a loop of prebuilt URLs.
- Stop and reassess after each detail note; do not auto-advance through a
  result set.

## Stop-loss (fuse)

On any of these signals, stop immediately, do **not** retry, and do **not**
hard-fetch:

- captcha / slider verification;
- login wall or forced re-auth redirect;
- repeated risk pages / 403 / account-level error screens.

Preserve evidence: screenshot, current URL, page title, and a short text
snapshot into the task artifact. End the session cleanly (close only owned
tabs) and record the stop in the run log.

## Session spacing

- Wait ≥ 30 minutes between sessions that use the same logged-in profile.
- Prefer fewer, smaller sessions over one long crawl.

## When to escalate

If a site change makes these rules impossible to satisfy while completing the
task, stop and report rather than relaxing the fuse.
