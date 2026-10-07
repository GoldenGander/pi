# Personal finance project: roadmap

Credit card bonuses are phase 1. The project is meant to grow into tracking and optimizing the
rest of the user's finances, one verified step at a time. This file is the plan for that growth.
Status words: DONE, NOW, NEXT, LATER. Phases after NEXT are outlines and will change once real data exists.

## Principles (apply to every phase)

1. **Provenance.** Any number that drives a decision (rate, bonus, limit, tax rule) lives in a ledger entry with a
   source URL and an exact quote, read from the primary source. The model's memory is never a source.
   `claims.json` + `cardtool.py validate` is the pattern; later phases reuse it (one ledger per domain, same validator).
2. **Claude advises; the user acts.** Claude does not apply for products, move money, or log in to accounts.
   Anything that moves money or opens an account is a checklist item for the user.
3. **Read-only data access.** Transaction feeds are read-only (SimpleFIN). No credentials for the bank itself are ever stored.
4. **Privacy.** Secrets (SimpleFIN Access URL, API keys) only in the environment's secret store. Raw transactions
   and balances never go in this public-ish repo; they go in a private store (below). Only aggregates and
   decisions are committed.
5. **Gates, not momentum.** Each phase has an exit test. We do not start the next phase's money decisions until the
   previous phase's data is trustworthy.
6. **Don't spend to earn.** No optimization is worth carrying interest, missing a payment, or buying things to hit a threshold.
7. **Cheap and boring first.** Prefer a $1.50/month feed and a SQLite file over a SaaS dashboard unless the SaaS earns its price.

## Target architecture

```
SimpleFIN Bridge (read-only feed, ~24 requests/day)
        |  tracker.py sync / ingest.py   (scheduled; Access URL from secrets)
        v
Private store: SQLite file in a private repo or Drive (transactions, balances, account map)
        |  normalize -> dedupe by (account, id) -> categorize (rules file, reviewed)
        v
Analytics layer (python, tested):  spend by category/month, bonus progress, utilization, net worth
        |
        +--> Decision tools (read ledgers):  cardtool.py plan / best-card-per-category / fee-vs-benefit
        +--> Reports + reminders:  monthly summary, deadline alerts (scheduled routine or notification)
```

Decisions that need the user, listed once so nothing blocks silently:
- Where the private store lives (private GitHub repo vs Google Drive file).
- Whether to create the scheduled routine (a recurring cloud session). Nothing recurring exists yet.
- Create the SimpleFIN account and generate the setup token. Claude cannot do this.

## Phases

### Phase 0: Foundations (DONE)
Provenance ledger and validator; EV calculator; bonus tracker with mock-tested parsing.
Exit: `cardtool.py validate` passes; every number in `STRATEGY.md` traces to a quote.

### Phase 1: Card bonuses (NOW)
Pre-qualify, apply to one card at a time (see `STRATEGY.md`), track each minimum spend.
Tracking in this phase, in order of preference:
1. Each issuer's own app/alerts for spend progress (zero integration, verify it exists per issuer).
2. `tracker.py` with manual open dates and `spend_to_date` entries.
3. SimpleFIN sync (Phase 2) once the first card is open and the feed shows it.
Exit: first bonus received and recorded; tracker agrees with the issuer's statement to the dollar.
That agreement is the test that the sync is trustworthy enough for phase 2 decisions.

### Phase 2: Data ingestion and storage (NEXT, starts when the first card is open)
- Create SimpleFIN setup token (user), store Access URL as a secret.
- `ingest.py`: pull accounts (checking at Founders FCU if supported, each card), keep a 5-day window overlap
  (recommended by SimpleFIN), store to SQLite with unique key (account id, transaction id). Respect the
  90-day-per-request and ~24-requests/day limits; one scheduled run per day is plenty.
- Account map file: friendly name, issuer, type, open date, bonus terms id. Handle SimpleFIN quirks: pending
  transactions excluded by default, `posted` may be 0, amounts are strings, negative = money out.
- Health checks: stale feed (no new data in 3 days), account missing, auth failure (402/403) -> notify the user.
- Fallback if Founders FCU or a card is unsupported: that account is tracked from CSV/OFX the user chooses to
  export occasionally, or not tracked. (Unresolved: Founders FCU support, only a name match was found.)
Exit: 30 days of data; balances reconcile with statements; zero duplicate transactions.

### Phase 3: Spend analytics (NEXT)
- Categorization: a rules file (merchant pattern -> category), reviewed by the user monthly; unmatched go to a review list.
- Reports: monthly spend by category, rent vs non-rent, recurring charges and subscriptions, month-over-month change.
- Output feeds the biggest open input to the card plan: the real category mix. Re-run
  `cardtool.py plan --mix ...` with measured data; replace the assumed mix.
- Budget targets only if the user wants them; start with observation.
Exit: 3 months of categorized data; mix used in the card plan is measured.

### Phase 4: Ongoing rewards optimization (LATER)
- Best card per category (from the ledger, not memory) and a "which card for what" cheat sheet.
- Calendar: Chase quarterly activation, quarter changes, bonus windows, card anniversaries.
- Annual decisions per card: keep, downgrade or close (no-fee cards are kept for account age), retention offers.
- Re-open the sign-up bonus pipeline when cooldowns expire (24-48 months, from verified rules). The tracker already
  computes next-eligible dates.
- Consider rent: only if a payment method's fee is below the reward it earns, using sourced fees.
Exit: realized cash back per month vs the predicted cash back from the ledger is within 10%.

### Phase 5: Credit health (LATER)
- Track utilization per card and overall, hard inquiries, account ages, a 5/24-style application counter.
- Score monitoring from a free issuer-provided source (e.g. a card's own score view); log the score monthly.
- Rules the system enforces as reminders: pay the full statement balance; keep reported utilization under about 10-30%;
  no application if the last one was under 3 months ago or if any late payment exists.
Exit: score trend recorded for 6 months; applications always preceded by the checklist.

### Phase 6: Cash and savings optimization (LATER)
- Emergency fund target (user's choice of months of expenses), and where it sits (high-yield savings, credit union).
- Compare savings rates and bank sign-up bonuses using the same provenance ledger. Bank bonuses often need direct deposit
  and minimum balances, so they need the user's income details first.
- Founders FCU rates and products, read from the primary source when reachable (the site blocked automated reads).
Exit: emergency fund funded; savings rate benchmarked against a sourced alternative.

### Phase 7: Taxes, retirement and investing (LATER, needs the user's income details)
Software engineer income is likely W-2 with possible equity. Inputs needed: employer 401(k) match, HSA eligibility,
equity compensation, state of residence. Tools here must cite IRS/plan documents for limits and rules, never memory.
Output: a prioritized list (match first, high-interest debt, emergency fund, tax-advantaged accounts) with the user's own numbers.
Claude gives analysis, not investment or tax advice: flag when a professional is warranted.
Exit: yearly contribution plan exists and every limit in it is cited.

### Phase 8: Net worth and goals dashboard (LATER)
- One view: assets, liabilities, net worth over time, savings rate, progress toward user-set goals.
- Delivered as a private artifact or a generated report; no data leaves the private store except aggregates the user chooses to share.

## Cadence once running

| Frequency | What happens | How |
|---|---|---|
| Daily | Pull transactions, update bonus progress | scheduled script (needs user's go-ahead) |
| Weekly | Uncategorized merchant review list; feed health check | report |
| Monthly | Spend report, tracker status, upcoming deadlines, cooldown dates | report/notification |
| Quarterly | Card category activation, re-check ledger offers for staleness | reminder |
| Annually | Card keep/close review, fee vs benefit, tax and contribution plan | review |

## Repo layout (proposed; do not reorganize until phase 2 starts)
`credit-cards/` now; when phase 2 begins move to a `finance/` project with `ledgers/` (provenance JSON per domain),
`tools/` (cardtool, tracker, ingest), `docs/` (strategy, roadmap, handoff). Raw data stays in the private store.
Keep one handoff file current at the end of every session so a fresh session can continue cold.

## Next concrete steps for tracking (in order)
1. User creates SimpleFIN account and setup token (Phase 2 prerequisite, can wait until the first card is open).
2. Decide the private store location.
3. Write `ingest.py` and test against SimpleFIN's documented response format with mock data, then against the live feed
   with the first card; compare to the statement.
4. Add the account map and categorization rules.
5. Decide on the scheduled routine for the daily/monthly runs.
