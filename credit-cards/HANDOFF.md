# Credit card optimization: handoff

Branch: `claude/credit-card-optimization-2f6gzv` (repo goldengander/pi, dir `credit-cards/`).
Written 2026-10-07 from a cloud session whose network policy blocked issuer sites.

## Goal
Maximize total EV from credit card sign-up bonuses, "churning-lite": one card at a time,
start small, expand later. Track spend toward each bonus automatically.

## User profile (as stated by the user, unverified)
- Credit score about 690 (fair/good). Currently has no credit cards.
- Banks with Founders Federal Credit Union, debit card only.
- Non-rent spend about $500/month (about $6,000/yr). Main expense is rent.
- Wants cash back only. Fine with an ongoing loop, but start small.
- Software engineer; can add connectors and edit environment settings themselves.
- Does not want to export/upload statements by hand; wants automation.

## Rules the user set
- Every claim about a card needs documented provenance. An earlier wrong claim
  (Wells Fargo Active Cash bonus stated as $200; current sources say $100) is why.
- Treat anything not read from the issuer's own page as unverified.

## Status (updated 2026-10-07, second session, network access to issuer sites worked)
Read `STRATEGY.md` first. All card terms were re-read from issuer pages (headless Chromium);
`claims.json` now has 43 primary_verified claims, each with an exact quote that
`python3 -I cardtool.py validate` checks against the saved page text in `evidence/`.
Resolved: Wells Fargo bonus is $100. Corrected: WF 4-month rule, BofA $2,500/qtr combined cap.
Found: Capital One bonus cards are the "Excellent credit" tier; see STRATEGY.md.

Tools: `cardtool.py validate|ev|plan`, `tracker.py status|sync|claim` (sync's live API call is untested).
Remaining work needs the user: pre-qualification checks, applying, SimpleFIN setup token, spend mix.
Safety notes below still apply.

## Safety notes
- Claude cannot apply for cards or touch the user's bank; the user submits applications.
- Pay balances in full every month. Never spend just to hit a minimum.
- A one-time rent payment through a payment service (about 2.5-3% fee) to hit a minimum might
  be positive EV; fee and issuer treatment are unverified.
