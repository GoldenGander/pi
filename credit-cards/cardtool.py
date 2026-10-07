#!/usr/bin/env python3
"""Validate the claims ledger and compute a provenance-aware floor EV.

    python3 cardtool.py validate
    python3 cardtool.py ev --annual-spend 6000 [--allow-secondary]
    python3 cardtool.py plan --monthly-spend 500 [--mix groceries=.3,dining=.15] [--p card=0.6]

The EV is a floor: welcome bonus plus the flat base rate on annual spend.
It ignores category bonuses, which need your spending mix and sourced caps.
A card is ranked only if every claim it uses is acceptable; otherwise the
output says which claim blocks it.
"""
import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

LEDGER = Path(__file__).with_name("claims.json")
ISSUER_DOMAINS = (
    "wellsfargo.com", "chase.com", "bankofamerica.com", "citi.com", "capitalone.com", "discover.com",
)
STATUSES = {"primary_verified", "secondary_reported", "conflicting", "unsourced"}


def load():
    return json.loads(LEDGER.read_text())["claims"]


def host_is_issuer(url):
    host = urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in ISSUER_DOMAINS)


def validate(claims):
    errors, seen = [], set()
    for c in claims:
        cid = c.get("id", "<missing id>")
        if cid in seen:
            errors.append(f"{cid}: duplicate id")
        seen.add(cid)
        st = c.get("status")
        if st not in STATUSES:
            errors.append(f"{cid}: bad status {st!r}")
            continue
        if st == "unsourced":
            if c.get("source_url"):
                errors.append(f"{cid}: unsourced claims must have source_url null")
            continue
        if not c.get("source_url"):
            errors.append(f"{cid}: {st} requires source_url")
        elif st == "primary_verified" and not host_is_issuer(c["source_url"]):
            errors.append(f"{cid}: primary_verified but {c['source_url']} is not an issuer domain")
        if st == "primary_verified" and c.get("evidence") != "page_read":
            errors.append(f"{cid}: primary_verified requires evidence=page_read")
        if st == "primary_verified":
            errors.extend(check_quote(c))
        if st == "conflicting" and not c.get("conflicts"):
            errors.append(f"{cid}: conflicting requires conflicts[]")
    return errors


def norm(t):
    return " ".join(t.split())


def check_quote(c):
    cid = c["id"]
    if not c.get("quote") or not c.get("evidence_file"):
        return [f"{cid}: primary_verified requires quote and evidence_file"]
    path = LEDGER.parent / c["evidence_file"]
    if not path.exists():
        return [f"{cid}: evidence_file {c['evidence_file']} missing"]
    if norm(c["quote"]) not in norm(path.read_text()):
        return [f"{cid}: quote not found in {c['evidence_file']}"]
    return []


def usable(claim, allow_secondary):
    ok = {"primary_verified"} | ({"secondary_reported"} if allow_secondary else set())
    return claim["status"] in ok


def ev(claims, annual_spend, allow_secondary):
    by_card = {}
    for c in claims:
        by_card.setdefault(c["card"], {})[c["field"]] = c
    rows = []
    for card, f in by_card.items():
        bonus, rate = f.get("welcome_bonus"), f.get("rates")
        if not bonus or not rate or bonus["value"].get("amount") is None:
            continue
        blockers = [x["id"] + f" ({x['status']})" for x in (bonus, rate) if not usable(x, allow_secondary)]
        if blockers:
            rows.append((card, None, "blocked by " + ", ".join(blockers)))
            continue
        total = bonus["value"]["amount"] + rate["value"]["base"] * annual_spend
        used = f"{bonus['id']}={bonus['status']}, {rate['id']}={rate['status']}"
        rows.append((card, total, used))
    return sorted(rows, key=lambda r: (r[1] is None, -(r[1] or 0)))


MIX_ASSUMPTION = {"groceries": 0.30, "dining": 0.15, "drugstores": 0.03, "gas": 0.07,
                  "streaming": 0.05, "entertainment": 0.02, "other": 0.38}
CARD_ORDER_DEFAULT = ["Chase Freedom Flex", "Citi Double Cash", "Capital One Savor",
                      "Bank of America Customized Cash Rewards", "Wells Fargo Active Cash"]


def by_card(claims):
    out = {}
    for c in claims:
        out.setdefault(c["card"], {})[c["field"]] = c
    return out


def phase_rate(card, f, mix, quarter_cap_spend):
    """Blended cash-back rate for one quarter of spending on `card` (verified rates only)."""
    r = f["rates"]["value"]
    base = r["base"]
    g = lambda *ks: sum(mix.get(k, 0) for k in ks)
    if card == "Chase Freedom Flex":  # Q4 2026 and Q1 2027 both include groceries; Q4 adds dining
        share = g("groceries", "dining")
        capped = min(share * quarter_cap_spend, r["rotating_cap_per_quarter"])
        # conservative: ignores the 3% dining/drugstore tier on the uncapped remainder
        return (capped * r["categories"]["rotating"] + (quarter_cap_spend - capped) * base) / quarter_cap_spend
    if card == "Chase Freedom Unlimited":
        return base + (r["categories"]["dining"] - base) * g("dining", "drugstores")
    if card == "Capital One Savor":
        return base + (r["categories"]["groceries"] - base) * g("groceries", "dining", "entertainment", "streaming")
    if card == "Bank of America Customized Cash Rewards":
        best = max(("gas", "dining", "drugstores"), key=lambda k: mix.get(k, 0))
        cat, groc = g(best) * quarter_cap_spend, g("groceries") * quarter_cap_spend
        cap = r["combined_cap_per_quarter"]
        cat_used = min(cat, cap)
        groc_used = min(groc, cap - cat_used)
        extra = cat_used * (r["categories"]["choice"] - base) + groc_used * (r["categories"]["grocery_wholesale"] - base)
        return base + extra / quarter_cap_spend
    return base  # flat-rate cards (Citi, Wells Fargo, Quicksilver)


def plan(claims, monthly, order, mix, p_approve):
    cards = by_card(claims)
    fallback = max((c for c in cards if c in ("Citi Double Cash", "Wells Fargo Active Cash")),
                   key=lambda c: cards[c]["rates"]["value"]["base"])
    print(f"Assumed monthly non-rent spend ${monthly:,.0f}; mix {mix}")
    print(f"Each new card gets all non-rent spend for 3 months (one quarter); afterwards spend goes to {fallback}.")
    print(f"{'phase':5s} {'card':42s} {'bonus':>6s} {'p':>5s} {'spend':>7s} {'rate':>6s} {'cashback':>9s} {'EV':>7s}")
    total = 0.0
    for i, card in enumerate(order, 1):
        f = cards[card]
        for k in ("welcome_bonus", "rates"):
            if f[k]["status"] != "primary_verified":
                print(f"  {card}: {k} not primary_verified; skipped")
                break
        else:
            q = monthly * 3
            rate = phase_rate(card, f, mix, q)
            cb = q * rate
            bonus = f["welcome_bonus"]["value"]["amount"]
            if f["welcome_bonus"]["value"]["min_spend"] > q:
                print(f"  {card}: min spend exceeds 3 months of spend; bonus needs a longer window")
            p = p_approve.get(card, 1.0)
            ev = p * (bonus + cb) + (1 - p) * q * cards[fallback]["rates"]["value"]["base"]
            total += ev
            print(f"{i:<5d} {card:42s} {bonus:>6d} {p:>5.2f} {q:>7,.0f} {rate:>6.3f} {cb:>9,.0f} {ev:>7,.0f}")
    print(f"Total over {3 * len(order)} months: ${total:,.0f}  (approval p defaults to 1.0 = optimistic)")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    e = sub.add_parser("ev")
    e.add_argument("--annual-spend", type=float, required=True)
    e.add_argument("--allow-secondary", action="store_true",
                   help="Include secondary_reported claims (unverified).")
    pl = sub.add_parser("plan")
    pl.add_argument("--monthly-spend", type=float, required=True)
    pl.add_argument("--order", default=",".join(CARD_ORDER_DEFAULT))
    pl.add_argument("--mix", default="", help="e.g. groceries=0.3,dining=0.15 (rest = other). Default is an ASSUMED mix.")
    pl.add_argument("--p", action="append", default=[], help="approval probability, e.g. 'Citi Double Cash=0.7'")
    a = p.parse_args()

    claims = load()
    errs = validate(claims)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    if a.cmd == "validate":
        counts = {}
        for c in claims:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        print("ledger ok:", counts)
        return 0

    if a.cmd == "plan":
        mix = dict(MIX_ASSUMPTION)
        if a.mix:
            mix = {k: float(v) for k, v in (x.split("=") for x in a.mix.split(","))}
            mix["other"] = max(0.0, 1 - sum(v for k, v in mix.items() if k != "other"))
        probs = {k: float(v) for k, v in (x.rsplit("=", 1) for x in a.p)}
        plan(claims, a.monthly_spend, a.order.split(","), mix, probs)
        return 0

    if a.allow_secondary:
        print("WARNING: using unverified secondary_reported claims.\n")
    for card, total, note in ev(claims, a.annual_spend, a.allow_secondary):
        print(f"{card:42s} {'BLOCKED' if total is None else f'${total:,.0f} floor':>12s}  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
