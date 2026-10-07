#!/usr/bin/env python3
"""Tests for tracker.py against a local mock of the SimpleFIN /accounts endpoint. Run: python3 -I test_tracker.py"""
import base64
import json
import os
import sys
import tempfile
import threading
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).parent))
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
import tracker  # noqa: E402

ts = lambda d: int(datetime.fromisoformat(d + "T12:00:00+00:00").timestamp())
TX = [
    {"id": "1", "posted": ts("2026-10-08"), "amount": "-120.00", "description": "GROCERY"},
    {"id": "2", "posted": ts("2026-10-09"), "amount": "-80.50", "description": "RESTAURANT"},
    {"id": "3", "posted": ts("2026-10-10"), "amount": "20.00", "description": "RETURN STORE"},
    {"id": "4", "posted": ts("2026-10-11"), "amount": "500.00", "description": "ONLINE PMT RECEIVED"},
    {"id": "5", "posted": ts("2026-10-12"), "amount": "-30.00", "description": "PENDING", "pending": True},
    {"id": "6", "posted": ts("2026-09-30"), "amount": "-999", "description": "BEFORE OPEN"},
    {"id": "7", "posted": ts("2026-10-13"), "amount": "-25.00", "description": "INTEREST CHARGE PURCHASES"},
    {"id": "8", "posted": ts("2027-02-01"), "amount": "-500", "description": "AFTER WINDOW"},
    {"id": "9", "posted": ts("2026-12-20"), "amount": "-300.00", "description": "LATE PURCHASE"},
]
REQS, AUTH = [], []


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlsplit(self.path).query)
        lo, hi = int(q["start-date"][0]), int(q["end-date"][0])
        assert hi - lo <= 90 * 86400, "range over 90 days"
        REQS.append((lo, hi))
        AUTH.append(self.headers.get("Authorization"))
        tx = [t for t in TX if lo <= t["posted"] < hi]
        body = json.dumps({"errors": [], "accounts": [{"id": "A1", "name": "Freedom Flex", "org": {"name": "Chase"}, "transactions": tx}]}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


srv = HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()

# 1. classification
s, e = date(2026, 10, 7), date(2027, 1, 5)
assert tracker.spend_from_transactions(TX, s, e) == 120 + 80.5 - 20 + 300, tracker.spend_from_transactions(TX, s, e)

# 2. add_months clamps and handles leap years
assert tracker.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28) and tracker.add_months(date(2027, 2, 28), 12) == date(2028, 2, 28)
assert tracker.add_months(date(2026, 10, 7), 48) == date(2030, 10, 7)

# 3. cooldown: BofA has none on its page, so no "verified" label
assert tracker.cooldown_note("Bank of America Customized Cash Rewards")[0] is None
assert tracker.cooldown_note("Citi Double Cash")[0] == 48

# 4. end-to-end sync over a >89-day span, twice (idempotent), with percent-encoded credentials
with tempfile.TemporaryDirectory() as d:
    tracker.TRACKER, tracker.TXNS = Path(d) / "t.json", Path(d) / "x.json"
    tracker.TRACKER.write_text(json.dumps({"cards": [
        {"card": "Citi Double Cash", "status": "open", "opened": "2026-10-07", "account_match": "flex"}]}))  # 180-day window
    os.environ["SIMPLEFIN_ACCESS_URL"] = f"http://us%40er:p%2Fw@127.0.0.1:{srv.server_port}/simplefin"
    for _ in range(2):
        tracker.sync(date(2027, 2, 15))
    got = json.loads(tracker.TRACKER.read_text())["cards"][0]["spend_to_date"]
    assert got == 120 + 80.5 - 20 + 300 + 500, got  # tx 8 (2027-02-01) is inside Citi's 180-day window; payment, fee, pending, pre-open excluded
    assert len(REQS) >= 4 and all(h - l <= 90 * 86400 for l, h in REQS), REQS
    assert AUTH[0] == "Basic " + base64.b64encode(b"us@er:p/w").decode(), AUTH[0]
    tracker.status(date(2027, 2, 15))
print("ok")
