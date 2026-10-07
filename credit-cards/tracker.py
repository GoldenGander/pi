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
CLAIMS = HERE / "claims.json"
BUFFER = 1.15  # aim to spend 15% over the minimum: refunds/returns and posting delays can eat margin
PAYMENT = re.compile(r"payment|autopay|thank you|ach credit", re.I)


def load(p):
    return json.loads(p.read_text())


def bonus_terms(card):
    for c in load(CLAIMS)["claims"]:
        if c["card"] == card and c["field"] == "welcome_bonus" and c["status"] == "primary_verified":
            return c["value"]
    raise SystemExit(f"no primary_verified welcome_bonus for {card!r} in claims.json")


def cooldown_months(card):
    for c in load(CLAIMS)["claims"]:
        if c["card"] == card and c["field"] == "bonus_restriction" and c["status"] == "primary_verified":
            m = re.search(r"(\d+) months", c["value"])
            return int(m.group(1)) if m else None
    return None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    last = [31, 29 if (d.year + y) % 4 == 0 and ((d.year + y) % 100 or (d.year + y) % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m]
    return date(d.year + y, m + 1, min(d.day, last))


def spend_from_transactions(txns, since):
    """Net purchases since `since` (date): charges minus refunds; card payments ignored."""
    total = 0.0
    for t in txns:
        if t.get("pending"):
            continue
        posted = datetime.fromtimestamp(t["posted"], timezone.utc).date()
        if posted < since:
            continue
        amt = float(t["amount"])
        if amt < 0:
            total += -amt
        elif not PAYMENT.search(t.get("description", "")):
            total -= amt
    return round(max(total, 0.0), 2)


def http(url, method="GET", data=None):
    from urllib.parse import urlsplit, urlunsplit
    sp = urlsplit(url)
    req = urllib.request.Request(urlunsplit((sp.scheme, sp.hostname + (f":{sp.port}" if sp.port else ""), sp.path, sp.query, "")),
                                 method=method, data=data)
    if sp.username:
        tok = base64.b64encode(f"{sp.username}:{sp.password}".encode()).decode()
        req.add_header("Authorization", "Basic " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def fetch_accounts(access_url, start):
    end = int(time.time()) + 86400
    start_ts = max(int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp()), end - 89 * 86400)
    body = http(f"{access_url.rstrip('/')}/accounts?version=2&start-date={start_ts}&end-date={end}")
    data = json.loads(body)
    for e in data.get("errors", []):
        print("SimpleFIN:", e, file=sys.stderr)
    return data["accounts"]


def sync():
    url = os.environ.get("SIMPLEFIN_ACCESS_URL")
    if not url:
        raise SystemExit("set SIMPLEFIN_ACCESS_URL (see: tracker.py claim)")
    t = load(TRACKER)
    opened = [c for c in t["cards"] if c["status"] == "open"]
    if not opened:
        print("no open cards to sync")
        return
    start = min(date.fromisoformat(c["opened"]) for c in opened)
    accounts = fetch_accounts(url, start)  # one request per run; the bridge allows ~24/day
    for c in opened:
        hits = [a for a in accounts if c["account_match"].lower() in (a["name"] + " " + a.get("org", {}).get("name", "")).lower()]
        if len(hits) != 1:
            print(f"{c['card']}: {len(hits)} accounts match {c['account_match']!r}; not updated", file=sys.stderr)
            continue
        c["spend_to_date"] = spend_from_transactions(hits[0]["transactions"], date.fromisoformat(c["opened"]))
        c["last_sync"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    TRACKER.write_text(json.dumps(t, indent=2) + "\n")


def status(today):
    for c in load(TRACKER)["cards"]:
        line = f"{c['card']:42s} {c['status']:12s}"
        if c["status"] in ("open", "bonus_earned"):
            terms = bonus_terms(c["card"])
            opened = date.fromisoformat(c["opened"])
            end = opened + timedelta(days=terms["window_days"])
            spent, need = c.get("spend_to_date", 0.0), terms["min_spend"]
            left_days = (end - today).days
            if c["status"] == "bonus_earned":
                line += f" bonus earned; same-card bonus again allowed from {add_months(opened, cooldown_months(c['card']) or 48)} (issuer rule, verified)"
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
        sync()
    else:
        print(http(base64.b64decode(a.setup_token).decode().strip(), method="POST", data=b""))


if __name__ == "__main__":
    main()
