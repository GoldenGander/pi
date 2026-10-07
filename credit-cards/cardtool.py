#!/usr/bin/env python3
"""Validate the claims ledger and compute a provenance-aware floor EV.

    python3 cardtool.py validate
    python3 cardtool.py ev --annual-spend 6000 [--allow-secondary]

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
    "wellsfargo.com", "chase.com", "bankofamerica.com", "citi.com", "capitalone.com",
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
        if st == "conflicting" and not c.get("conflicts"):
            errors.append(f"{cid}: conflicting requires conflicts[]")
    return errors


def usable(claim, allow_secondary):
    ok = {"primary_verified"} | ({"secondary_reported"} if allow_secondary else set())
    return claim["status"] in ok


def ev(claims, annual_spend, allow_secondary):
    by_card = {}
    for c in claims:
        by_card.setdefault(c["card"], {})[c["field"]] = c
    rows = []
    for card, f in by_card.items():
        bonus, rate = f.get("welcome_bonus"), f.get("base_rate")
        if not bonus or not rate:
            continue
        blockers = [x["id"] + f" ({x['status']})" for x in (bonus, rate) if not usable(x, allow_secondary)]
        if blockers:
            rows.append((card, None, "blocked by " + ", ".join(blockers)))
            continue
        total = bonus["value"]["amount"] + rate["value"] * annual_spend
        used = f"{bonus['id']}={bonus['status']}, {rate['id']}={rate['status']}"
        rows.append((card, total, used))
    return sorted(rows, key=lambda r: (r[1] is None, -(r[1] or 0)))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    e = sub.add_parser("ev")
    e.add_argument("--annual-spend", type=float, required=True)
    e.add_argument("--allow-secondary", action="store_true",
                   help="Include secondary_reported claims (unverified).")
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

    if a.allow_secondary:
        print("WARNING: using unverified secondary_reported claims.\n")
    for card, total, note in ev(claims, a.annual_spend, a.allow_secondary):
        print(f"{card:42s} {'BLOCKED' if total is None else f'${total:,.0f} floor':>12s}  {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
