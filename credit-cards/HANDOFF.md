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

## What exists
- `claims.json`: 19 claims, each with source_url, evidence type and status.
  Status counts: 1 conflicting, 14 secondary_reported, 4 unsourced, 0 primary_verified.
- `cardtool.py validate`: schema/provenance checks.
- `cardtool.py ev --annual-spend 6000 [--allow-secondary]`: floor EV (bonus + flat base rate).
  Strict mode ranks nothing until claims are primary_verified.
- No tracker, no sync script, no scheduled routine yet.

## Candidate cards (all unverified, see claims.json for sources)
Chase Freedom Flex, Chase Freedom Unlimited, Wells Fargo Active Cash, Citi Double Cash,
Capital One Savor, Bank of America Customized Cash Rewards.
Earlier chat estimates of year-1 value for BofA (~$385), Flex (~$330) and Savor (~$300)
relied on unsourced base rates and a recalled BofA category cap; do not trust them.

## Open questions / unsourced
- Wells Fargo Active Cash bonus: $100 vs $200.
- Base rates for Chase Flex, Savor, BofA; Savor annual fee; BofA 6% first-year cap and
  how it combines with the 3% category; Flex Q4 2026 categories.
- User's non-rent spending mix by category (decides category cards vs flat-rate cards).
- Whether SimpleFIN supports Founders FCU (search found nothing either way).
- SimpleFIN protocol details (handshake, history limit, request cap) are from memory.

## Next steps, in order
1. In an environment that can reach the issuer sites, read each issuer's card page and terms
   (wellsfargo.com, chase.com, bankofamerica.com, citi.com, capitalone.com). For each
   claim set `status: primary_verified`, `evidence: page_read`, the issuer URL, and fix values.
   Resolve the Active Cash conflict. Run `python3 -I cardtool.py validate`.
2. Get the user's spend-by-category, then extend the EV calc for category cards using sourced caps.
3. User runs issuer pre-qualification (soft pull) for the top candidates. Apply to one card.
   Chase's 5/24 rule favors applying to Chase first, while the user has no cards;
   Chase approval for a thin file at 690 is the risk.
4. After approval: check SimpleFIN supports the card issuer (and Founders), read the SimpleFIN
   protocol docs, then write a daily sync script. Keep the Access URL in secrets, never in git.
   Do not commit transaction data to this repo; use a private repo or Drive.
5. Add a bonus tracker (card, open date, minimum, window end, progress, next-eligible date from
   each issuer's cooldown rule) and a scheduled monthly reminder.

## Safety notes
- Claude cannot apply for cards or touch the user's bank; the user submits applications.
- Pay balances in full every month. Never spend just to hit a minimum.
- A one-time rent payment through a payment service (about 2.5-3% fee) to hit a minimum might
  be positive EV; fee and issuer treatment are unverified.
