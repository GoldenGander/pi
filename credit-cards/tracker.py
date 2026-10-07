#!/usr/bin/env python3
"""Bonus-spend tracker, fed by SimpleFIN Bridge (or by hand).

    python3 tracker.py status [--today YYYY-MM-DD]
    python3 tracker.py sync            # needs SIMPLEFIN_ACCESS_URL in the environment
    python3 tracker.py claim <setup_token>   # one-time: prints the Access URL; store it as a secret

tracker.json holds only per-card totals, never transactions. Never commit the Access URL.
Bonus terms (min spend, window) come from the primary_verified entries in claims.json.
Progress is an estimate: the issuer's statement is authoritative.
"""
import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).parent
TRACKER = HERE / "tracker.json"
TXNS = HERE / "tracker_txns.json"  # gitignored: per-card {transaction id: contribution}, no merchants
CLAIMS = HERE / "claims.json"
BUFFER = 1.15  # aim to spend 15% over the minimum: refunds/returns and posting delays can eat margin
PAYMENT = re.compile(r"payment|pmt|autopay|auto pay|thank you|\bach\b|bill pay|payoff|online transfer", re.I)
NOT_SPEND = re.compile(r"interest charge|finance charge|late fee|annual fee|membership fee|cash advance", re.I)


def load(p):
    return json.loads(p.read_text())


def bonus_terms(card):  # primary_verified terms only
    for c in load(CLAIMS)["claims"]:
        if c["card"] == card and c["field"] == "welcome_bonus" and c["status"] == "primary_verified":
            return c["value"]
    raise SystemExit(f"no primary_verified welcome_bonus for {card!r} in claims.json")


def cooldown_note(card):
    """Return (months, text). Only claims an issuer rule when a verified restriction states one."""
    for c in load(CLAIMS)["claims"]:
        if c["card"] == card and c["field"] == "bonus_restriction" and c["status"] == "primary_verified":
            m = re.search(r"(\d+) months", c["value"])
            if m:
                return int(m.group(1)), "issuer page, verified"
    return None, "not stated on the issuer page; check the offer terms"


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    yr = d.year + y
    leap = yr % 4 == 0 and (yr % 100 != 0 or yr % 400 == 0)
    last = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m]
    return date(yr, m + 1, min(d.day, last))


def contribution(t, start, end):
    """Signed effect of one transaction on net purchases inside [start, end], or None if it is not spend.

    Charges count. Returns/credits subtract. Card payments, fees, interest and cash advances are ignored.
    Pending transactions are ignored: they have not posted, and the bonus counts posted purchases."""
    if t.get("pending"):
        return None
    posted = datetime.fromtimestamp(t["posted"], timezone.utc).date()
    if not (start <= posted <= end):
        return None
    amt, desc = float(t["amount"]), t.get("description", "")
    if NOT_SPEND.search(desc) or (amt > 0 and PAYMENT.search(desc)):
        return None
    return -amt  # charge (amount < 0) -> positive spend; refund (amount > 0) -> negative


def spend_from_transactions(txns, start, end):
    return round(max(sum(v for v in (contribution(t, start, end) for t in txns) if v is not None), 0.0), 2)


def http(url, method="GET", data=None):
    from urllib.parse import unquote, urlsplit, urlunsplit
    sp = urlsplit(url)
    host = sp.hostname + (f":{sp.port}" if sp.port else "")
    req = urllib.request.Request(urlunsplit((sp.scheme, host, sp.path, sp.query, "")), method=method, data=data)
    if sp.username:
        tok = base64.b64encode(f"{unquote(sp.username)}:{unquote(sp.password or '')}".encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def fetch_accounts(access_url, start, end):
    """All accounts with transactions in [start, end], in <=89-day requests (SimpleFIN allows 90 days at a time)."""
    merged = {}
    lo = datetime.combine(start, datetime.min.time(), timezone.utc)
    stop = datetime.combine(end + timedelta(days=1), datetime.min.time(), timezone.utc)
    while lo < stop:
        hi = min(lo + timedelta(days=89), stop)
        url = f"{access_url.rstrip('/')}/accounts?version=2&start-date={int(lo.timestamp())}&end-date={int(hi.timestamp())}"
        data = json.loads(http(url))
        for e in data.get("errors", []):
            print("SimpleFIN:", e, file=sys.stderr)
        for a in data["accounts"]:
            m = merged.setdefault(a["id"], {**a, "transactions": {}})
            for t in a.get("transactions", []):
                m["transactions"][t["id"]] = t
        lo = hi
    for a in merged.values():
        a["transactions"] = list(a["transactions"].values())
    return list(merged.values())


def require(c, *keys):
    missing = [k for k in keys if not c.get(k)]
    if missing:
        raise SystemExit(f"tracker.json: {c.get('card')} is missing {', '.join(missing)}")


def sync(today):
    url = os.environ.get("SIMPLEFIN_ACCESS_URL")
    if not url:
        raise SystemExit("set SIMPLEFIN_ACCESS_URL (see: tracker.py claim)")
    t = load(TRACKER)
    state = load(TXNS) if TXNS.exists() else {}
    opened = [c for c in t["cards"] if c["status"] == "open"]
    if not opened:
        print("no open cards to sync")
        return
    for c in opened:
        require(c, "opened", "account_match")
    windows = {c["card"]: (date.fromisoformat(c["opened"]),
                           date.fromisoformat(c["opened"]) + timedelta(days=bonus_terms(c["card"])["window_days"])) for c in opened}
    # Fetch from the earliest open date (or 5 days before the last sync, the overlap SimpleFIN recommends) to today.
    lasts = [datetime.fromisoformat(c["last_sync"]).date() - timedelta(days=5) for c in opened if c.get("last_sync")]
    start = min(w[0] for w in windows.values()) if len(lasts) < len(opened) else max(min(lasts), min(w[0] for w in windows.values()))
    accounts = fetch_accounts(url, start, today)
    for c in opened:
        lo, hi = windows[c["card"]]
        hits = [a for a in accounts if c["account_match"].lower() in (a["name"] + " " + a.get("org", {}).get("name", "")).lower()]
        if len(hits) != 1:
            print(f"{c['card']}: {len(hits)} accounts match {c['account_match']!r}; not updated", file=sys.stderr)
            continue
        seen = state.setdefault(c["card"], {})
        for tx in hits[0]["transactions"]:
            v = contribution(tx, lo, hi)
            if v is not None:
                seen[tx["id"]] = v
            if v is None and float(tx["amount"]) >= 50 and not tx.get("pending") and not PAYMENT.search(tx.get("description", "")):
                print(f"review: ${float(tx['amount']):,.2f} credit ignored: {tx.get('description', '')!r}", file=sys.stderr)
            elif v is not None and v < -50:
                print(f"review: ${-v:,.2f} treated as a refund (subtracted): {tx.get('description', '')!r}", file=sys.stderr)
        c["spend_to_date"] = round(max(sum(seen.values()), 0.0), 2)
        c["last_sync"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    TXNS.write_text(json.dumps(state))
    TRACKER.write_text(json.dumps(t, indent=2) + "\n")


def status(today):
    for c in load(TRACKER)["cards"]:
        line = f"{c['card']:42s} {c['status']:12s}"
        if c["status"] in ("open", "bonus_earned"):
            require(c, "opened")
            terms = bonus_terms(c["card"])
            opened = date.fromisoformat(c["opened"])
            end = opened + timedelta(days=terms["window_days"])  # days, not calendar months: slightly early on purpose
            spent, need = c.get("spend_to_date", 0.0), terms["min_spend"]
            left_days = (end - today).days
            if c["status"] == "bonus_earned":
                months, how = cooldown_note(c["card"])
                line += (f" bonus earned; same-card bonus again from {add_months(opened, months)} ({how})" if months
                         else f" bonus earned; cooldown {how}")
            elif spent >= need:
                line += f" MINIMUM MET (${spent:,.0f}/${need}); confirm the bonus posts, then set status=bonus_earned"
            elif left_days < 0:
                line += f" WINDOW CLOSED {end} with ${spent:,.0f}/${need}"
            else:
                target = need * BUFFER
                line += (f" ${spent:,.0f}/${need} by {end} ({left_days}d left); put ~${max(target - spent, 0) / max(left_days, 1) * 30:,.0f}/mo "
                         f"on it to finish with a {round((BUFFER - 1) * 100)}% buffer")
        print(line)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--today", default=date.today().isoformat())
    sub.add_parser("sync")
    c = sub.add_parser("claim")
    c.add_argument("setup_token")
    a = p.parse_args()
    if a.cmd == "status":
        status(date.fromisoformat(a.today))
    elif a.cmd == "sync":
        sync(date.today())
    else:
        print(http(base64.b64decode(a.setup_token).decode().strip(), method="POST", data=b""))


if __name__ == "__main__":
    main()
