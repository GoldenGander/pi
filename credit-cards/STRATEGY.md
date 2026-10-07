# Credit card sign-up bonus strategy (cash back, one card at a time)

Written 2026-10-07. Every card number below comes from a `primary_verified` entry in
`claims.json`: the exact quote is stored in the entry, the page text is saved in `evidence/`,
and `python3 -I cardtool.py validate` fails if a quote is not found in its evidence file.
Offers change; re-read the issuer page on the day you apply (see "Before each application").

## Bottom line

- The sign-up bonuses are almost all of the money. At about $500/month of non-rent spending,
  the ongoing cash-back differences between these cards are $15-40 per quarter. Bonuses are $100-250 each.
- Every minimum spend fits inside normal spending: $500 in 3 months for most, $1,000 in 90 days (BofA),
  $1,500 in 6 months (Citi). No rent-payment tricks, no manufactured spending. Do not use them.
- Recommended sequence, one card at a time, about 3-4 months apart:
  1. **Chase Freedom Flex** ($250, limited-time offer; $0 fee).
  2. **Citi Double Cash** ($200 after $1,500 in 6 months; flat 2%).
  3. Then whichever of **Capital One Savor** ($200), **Bank of America Customized Cash Rewards** ($200)
     the pre-qualification checks say you can get, strongest first.
  4. **Wells Fargo Active Cash** ($100) last, or skip. It is the weakest bonus.
- The order is a default, not a promise. Which cards you can actually get at about a 690 score is the largest
  unknown, so the first action is a same-day round of soft-pull pre-qualification checks (below).
- Expected value: about $1,100 over 15 months if every application is approved, and about $700 under
  deliberately pessimistic approval odds (`cardtool.py plan`). Treat these as modelled, not promised.

## Verified facts (all from issuer pages read 2026-10-07)

| Card | Bonus | Min spend / window | Earn | Fee | Same-card bonus cooldown |
|---|---|---|---|---|---|
| Chase Freedom Flex | $250 (limited-time; page shows $200 struck out) | $500 / 3 months | 5% rotating on up to $1,500/qtr (activate), 3% dining + drugstores, 1% else | $0 | 24 months |
| Chase Freedom Unlimited | $200 | $500 / 3 months | 1.5%, 3% dining + drugstores | $0 | 24 months |
| Citi Double Cash | $200 | $1,500 / 6 months | 1% when you buy + 1% as you pay | $0 | 48 months |
| Capital One Savor | $200 | $500 / 3 months | 3% groceries (not Walmart/Target), dining, entertainment, streaming; 1% else | $0 | 48 months |
| Capital One Quicksilver | $200 | $500 / 3 months | 1.5% | $0 | 48 months |
| BofA Customized Cash Rewards | $200 | $1,000 / 90 days | 6% first year (3% after) in a chosen category + 2% grocery/wholesale, combined $2,500/qtr cap; 1% else | $0 | not on page |
| Wells Fargo Active Cash | **$100** | $500 / 3 months | 2% | $0 | 48 months; no 2nd WF consumer card if one opened in last **4** months |
| Discover it Cash Back | no spend bonus; matches all first-year cash back | none | 5% rotating (cap not on page), 1% else | $0 | n/a |
| Chase Freedom Rise | $25 credit for autopay | none | 1.5% | $0 | n/a |

Chase Flex Q4 2026 (Oct-Dec) categories: groceries (not Walmart/Target), dining, American Red Cross, up to $1,500,
activation required (activation opened Sept 15). Q1 2027: groceries and streaming.

### Corrections to earlier claims in this project

- Wells Fargo Active Cash bonus is **$100**, not $200 (issuer page). The $200 article is stale.
- Wells Fargo's second-card rule is **4 months** on the issuer page (the old ledger said 6).
- BofA's cap is **$2,500 per quarter combined** across the chosen category and grocery/wholesale.
  Earlier chat estimates (BofA ~$385, Flex ~$330, Savor ~$300 for year 1) were not sourced and are withdrawn.
- Capital One labels Savor and Quicksilver "Credit Level: EXCELLENT". It sells separate "for Good Credit"
  versions that show no cash bonus, and fair-credit versions with a $39 annual fee. At about 690 you may be
  offered a version without the $200 bonus. Do not take a card without a bonus, and do not pay a $39 fee.
- Citi's "2%" is 1% when you buy and 1% as you pay. It is 2% only if you actually pay the bill.

## Why this order

1. **Chase first.** The Chase "5/24" rule (denied if 5+ cards opened in 24 months) is only reported by third
   parties (`chase.5-24`, secondary; Chase does not publish it). You have no cards, so you are at 0/24 now.
   This plan opens 5 cards in about 15 months, so apply to Chase before the others and do not plan on another Chase card afterwards.
   The Flex has the highest verified bonus ($250) and it is limited-time, so it goes first.
   Its Q4 5% categories (groceries, dining) are likely to match everyday spending.
2. **Citi second.** Flat 2% (if you pay), $0 fee, only needs $1,500 in 6 months. It is the best default card for
   everything else, and every spend not needed for a bonus should go on it.
3. **Savor / BofA next, by pre-qualification result.** Both $200. Savor is easier to hit ($500) but sits in
   Capital One's Excellent tier. BofA needs $1,000 in 90 days and gives 6% in one chosen category for a year
   plus 2% groceries, which is the best category rate here if the spend matches.
4. **Wells Fargo last or never.** $100 is half the other bonuses. It is only worth it if the application is clean
   and you have no better card available.

Spacing: wait until the previous card's bonus has posted and about 3 months have passed before applying again.
This is my judgement, not an issuer rule: it limits stacked hard inquiries and new-account effects on a thin file.
Issuers' unpublished velocity rules (BofA 2/3/4 is secondary-reported) are also respected by this spacing.

## Before each application (the user must do this; Claude cannot apply)

1. **Same-day pre-qualification round (soft pull, no score impact per the issuer pages unless noted):**
   Capital One "Check My Eligibility" (page says no credit score impact), Discover pre-approval (page says checking
   does not impact score), Bank of America "See if you prequalify" (read the disclosure first). Chase's "Check for Offers" and
   Citi's tool: read the disclosure and proceed only if it says soft inquiry. Wells Fargo: no tool found.
   Record which card and bonus each tool shows. Skip any card the tool shows without the bonus.
2. Re-read the issuer's offer page on the day: bonus amount, minimum, window, and whether the offer is still live.
3. Apply to one card only. Do not apply to a second card within the same week.
4. After approval: set autopay to the full statement balance. Put all non-rent spend on this card.
   Activate Chase Flex categories each quarter.
5. Never spend to reach a minimum. Never carry a balance: APRs on these cards are 17.74%-28.74% across these cards
   (issuer pages), so one carried $1,000 balance costs more than a $200 bonus is worth.
6. After the minimum posts, confirm the bonus appears (issuers pay it on their own schedule), then mark the card
   `bonus_earned` in `tracker.json`.

## If things go wrong

- **Denied by Chase** (thin file at about 690): do not reapply for several months. Move the next pre-qualified card to
  first. A Chase checking/savings balance of $250+ is Chase's own stated way to improve odds on the Freedom Rise
  (`chase-rise.approval-hint`), a $25 starter card. It is a credit-building fallback, not a bonus play.
- **Pre-qual shows only "Good/Fair" tier Capital One offers:** skip Capital One for now.
- **Denied by two issuers in a row:** stop. Build history (Discover it, Chase Rise, or a credit-union card) for 6 months first.
  Founders FCU's own card is unresearched (the site blocked automated reads).
- **Score drops below about 660 or any late payment:** stop applying until it recovers.
- **Offer changed:** re-run `cardtool.py plan` after updating `claims.json` from the new page. Cards whose bonus is
  below $150 are not worth an application at this spend level.

## Automation (built, partly untested)

- `tracker.py status` reads `tracker.json` (card, open date, status) and `claims.json` (min spend, window), and prints
  progress, window end, and the monthly spend needed with a 15% buffer. Tested on mock data.
- `tracker.py sync` pulls card transactions from SimpleFIN Bridge and updates spend totals. The parsing is tested
  on mock transactions; the live API call is **untested** (no Access URL exists yet).
  SimpleFIN facts read from its own docs (2026-10-07): $1.50/month or $15/year; setup token -> POST claim -> Access URL;
  at most 90 days per request; about 24 requests/day. Its institution search lists Chase, Citi, Capital One, Bank of America,
  Wells Fargo, Discover, and one "Founders Federal Credit Union" (state unconfirmed). A listing does not prove
  the card feed works. Founders is only needed for the debit account; card tracking does not require it.
- The Access URL is a secret: keep it in an environment variable or secret store, never in git.
- Zero-cost alternative that needs no integration: each issuer's own app shows spend toward the bonus; the tracker
  then only needs open dates. This is the lowest-risk option if SimpleFIN fails for a card.
- Not set up: a scheduled monthly reminder. It needs a decision from the user (it creates a recurring cloud run).

## Open items and what is not verified

- The user's spending mix by category. `cardtool.py plan` uses an **assumed** mix (30% groceries, 15% dining, ...).
  It is only used for the category-card rates; the ranking of bonuses does not depend on it.
- Approval odds at about 690 with no cards. Issuers do not publish score cutoffs. Nothing here is a guarantee.
  The 690 score and "no cards" are user-stated and unverified (a 690 with no cards implies some other credit history).
- Chase 5/24, BofA 2/3/4: secondary sources only.
- Discover's quarterly 5% cap is not on its page.
- Whether SimpleFIN returns usable data for each card; Founders FCU card options; Plaid coverage.
- Tax treatment of bonuses: not researched.
