#!/usr/bin/env python3
"""
State Issue server, version 2.5.1
- Python standard library only (Python 3.8 or newer)
- SQLite database with a schema version and a migration step
- Serves the State Issue web application to computers on the local network
- Audit log: every saved change is recorded with the time, the computer
  it came from, the configured workstation name, and a count of what changed
  (no inmate or personal names are written to the log)
- Automatic backups: one per day (last 30 kept) and one per month (last 12 kept)
- Serves sw.js, the offline helper script used only by the computer that
  opens State Issue at 127.0.0.1/localhost (the host computer itself).
  Other computers on the network are unaffected.
Set STATE_ISSUE_DATA to put the database and backups in another folder.
"""
import http.server, socketserver, sqlite3, json, os, socket, webbrowser, threading, time, datetime
from urllib.parse import urlparse, parse_qs

APP_VERSION = "2.5.1"
SCHEMA_VERSION = 2
# Keep program files separate from the database location so the server can
# continue using a chosen data folder without moving the application itself.
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("STATE_ISSUE_DATA") or BASE
DB_PATH = os.path.join(DATA_DIR, "state_issue_v2.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
HTML_PATH = os.path.join(BASE, "Stateissue.html")
SEED_PATH = os.path.join(BASE, "seed.json")
SW_PATH = os.path.join(BASE, "sw.js")
HOST = "0.0.0.0"
PORT = int(os.environ.get("STATE_ISSUE_PORT", "8787"))
DAILY_KEEP = 30
MONTHLY_KEEP = 12
BACKUP_CHECK_SECONDS = 3600
TRACKED = [
    ("inmates", "inmate records"), ("requests", "requests"),
    ("requestItems", "request lines"), ("issues", "issues"),
    ("txns", "stock changes"), ("items", "item setup"),
    ("reminders", "reminders"), ("inventoryChecks", "inventory checks"),
    ("messages", "work queue items"), ("comments", "comments"),
]

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def dbconn():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH, isolation_level=None, timeout=10)

def migrate():
    """Create or upgrade the database to SCHEMA_VERSION. Safe to run every start."""
    c = dbconn()
    try:
        c.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = c.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        current = int(row[0]) if row else 0
        if current > SCHEMA_VERSION:
            raise RuntimeError("This database was made by a newer State Issue version. Do not run this server on it.")
        if current < 1:
            # Create the core tables in one transaction so a partial first
            # startup cannot leave the database marked as ready.
            c.execute("BEGIN IMMEDIATE")
            c.execute("CREATE TABLE IF NOT EXISTS app_state (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, state_json TEXT NOT NULL, updated_at TEXT NOT NULL)")
            c.execute("CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, workstation TEXT NOT NULL, revision INTEGER NOT NULL, summary TEXT NOT NULL)")
            c.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)", ("1",))
            c.execute("COMMIT")
            current = 1
        if current < 2:
            c.execute("BEGIN IMMEDIATE")
            cols = [r[1] for r in c.execute("PRAGMA table_info(audit_log)").fetchall()]
            if "who" not in cols:
                c.execute("ALTER TABLE audit_log ADD COLUMN who TEXT NOT NULL DEFAULT ''")
            c.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
            c.execute("COMMIT")
    finally:
        c.close()

def load_state():
    c = dbconn()
    try:
        row = c.execute("SELECT revision,state_json FROM app_state WHERE id=1").fetchone()
        if row:
            return row[0], json.loads(row[1])
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        state["rev"] = 0
        c.execute("INSERT OR IGNORE INTO app_state(id,revision,state_json,updated_at) VALUES(1,0,?,?)",
                  (json.dumps(state), now()))
        return 0, state
    finally:
        c.close()

def summarize(old, new):
    """Plain-language count of what changed. Counts only; never copies names."""
    parts = []
    for key, label in TRACKED:
        a = {x.get("id"): x for x in (old or {}).get(key, []) if isinstance(x, dict)}
        b = {x.get("id"): x for x in (new or {}).get(key, []) if isinstance(x, dict)}
        added = len(set(b) - set(a))
        removed = len(set(a) - set(b))
        changed = sum(1 for i in set(a) & set(b)
                      if json.dumps(a[i], sort_keys=True) != json.dumps(b[i], sort_keys=True))
        bits = []
        if added: bits.append("%d added" % added)
        if removed: bits.append("%d removed" % removed)
        if changed: bits.append("%d changed" % changed)
        if bits: parts.append("%s: %s" % (label, ", ".join(bits)))
    return "; ".join(parts) or "settings only"

def save_state(base_rev, state, workstation="unknown", who=""):
    # Compare-and-save: accepting only the revision a client actually read
    # prevents one workstation from silently replacing another's newer edits.
    c = dbconn()
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT revision, state_json FROM app_state WHERE id=1").fetchone()
        current = row[0] if row else 0
        if current != base_rev:
            c.execute("ROLLBACK")
            return False, current
        old = json.loads(row[1]) if row else None
        newrev = current + 1
        state["rev"] = newrev
        ts = now()
        payload = json.dumps(state, separators=(",", ":"))
        if row:
            cur = c.execute("UPDATE app_state SET revision=?,state_json=?,updated_at=? WHERE id=1 AND revision=?",
                            (newrev, payload, ts, current))
            if cur.rowcount != 1:
                c.execute("ROLLBACK")
                return False, current
        else:
            c.execute("INSERT INTO app_state(id,revision,state_json,updated_at) VALUES(1,?,?,?)", (newrev, payload, ts))
        c.execute("INSERT INTO audit_log(at,workstation,revision,summary,who) VALUES(?,?,?,?,?)",
                  (ts, workstation, newrev, summarize(old, state), who or ""))
        c.execute("COMMIT")
        with CHANGED:
            CHANGED.notify_all()
        return True, newrev
    except Exception:
        try:
            c.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        c.close()

def add_work_item(message, workstation="unknown", who=""):
    """Append a work item atomically and allocate its ID from the current state."""
    if not isinstance(message, dict):
        raise ValueError("invalid work item")
    if not isinstance(message.get("title"), str) or not message["title"].strip():
        raise ValueError("work item title is required")
    if not isinstance(message.get("body"), str) or not message["body"].strip():
        raise ValueError("work item details are required")

    c = dbconn()
    try:
        # SQLite serializes this write transaction. Reading the counter and
        # appending the item together gives concurrent posters distinct IDs.
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT revision,state_json FROM app_state WHERE id=1").fetchone()
        if not row:
            raise RuntimeError("application state is not initialized")
        current, raw = row
        old = json.loads(raw)
        state = json.loads(raw)
        messages = state.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("invalid work queue data")
        state["messages"] = messages
        seq = state.setdefault("seq", {})
        if not isinstance(seq, dict):
            raise ValueError("invalid sequence data")
        last_id = seq.get("message", 1000)
        last_id = last_id if isinstance(last_id, int) and last_id >= 0 else 1000
        for existing in messages:
            existing_id = str(existing.get("id", "")) if isinstance(existing, dict) else ""
            if existing_id.startswith("M") and existing_id[1:].isdigit():
                last_id = max(last_id, int(existing_id[1:]))
        item = dict(message)
        item["id"] = "M%d" % (last_id + 1)
        state["seq"]["message"] = last_id + 1
        state["messages"].append(item)

        newrev = current + 1
        state["rev"] = newrev
        ts = now()
        c.execute(
            "UPDATE app_state SET revision=?,state_json=?,updated_at=? WHERE id=1 AND revision=?",
            (newrev, json.dumps(state, separators=(",", ":")), ts, current),
        )
        c.execute(
            "INSERT INTO audit_log(at,workstation,revision,summary,who) VALUES(?,?,?,?,?)",
            (ts, workstation, newrev, summarize(old, state), who or ""),
        )
        c.execute("COMMIT")
        with CHANGED:
            CHANGED.notify_all()
        return newrev, item, state
    except Exception:
        try:
            c.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        c.close()

# Live updates: waiting clients are woken as soon as a save commits.
CHANGED = threading.Condition()

def current_revision():
    c = dbconn()
    try:
        row = c.execute("SELECT revision FROM app_state WHERE id=1").fetchone()
        return row[0] if row else 0
    finally:
        c.close()

def wait_for_revision(since, timeout):
    """Return as soon as the revision is newer than `since`, or after `timeout` seconds."""
    deadline = time.time() + timeout
    while True:
        rev = current_revision()
        if rev > since:
            return rev
        remaining = deadline - time.time()
        if remaining <= 0:
            return rev
        with CHANGED:
            CHANGED.wait(min(remaining, 1.0))

def recent_audit(limit=500):
    c = dbconn()
    try:
        rows = c.execute("SELECT at,workstation,revision,summary,who FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"at": r[0], "workstation": r[1], "revision": r[2], "summary": r[3], "who": r[4]} for r in rows]
    finally:
        c.close()

def boot_json(rev, state):
    """JSON for the page. Escaped so text like '</script>' typed into a note cannot break the page."""
    raw = json.dumps({"rev": rev, "state": state}, separators=(",", ":"))
    return (raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
               .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))

# ---------- backups ----------
def backup_now(name):
    # SQLite's backup API copies a consistent snapshot even if the server is
    # receiving saves while the copy is being made.
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = os.path.join(BACKUP_DIR, name)
    tmp = dest + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    src = dbconn()
    dst = sqlite3.connect(tmp)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.replace(tmp, dest)
    return dest

def verify_backup(path):
    """Check that a backup (or the live database) is intact and readable.
    Opens it read-only so it is never modified, prints a plain-language report,
    and returns True if the file passed every check, False otherwise."""
    if not os.path.exists(path):
        print("FILE NOT FOUND: %s" % path)
        return False
    try:
        c = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    except Exception as e:
        print("COULD NOT OPEN FILE: %s" % e)
        return False
    try:
        ok = True
        try:
            result = c.execute("PRAGMA integrity_check").fetchone()[0]
        except Exception as e:
            print("INTEGRITY CHECK FAILED TO RUN: %s" % e)
            return False
        if result != "ok":
            print("INTEGRITY CHECK FAILED: %s" % result)
            print("This file is damaged. Try an older backup instead.")
            return False
        print("Integrity check: OK")
        try:
            row = c.execute("SELECT revision, state_json, updated_at FROM app_state WHERE id=1").fetchone()
        except Exception as e:
            print("COULD NOT READ APPLICATION DATA: %s" % e)
            return False
        if not row:
            print("COULD NOT READ APPLICATION DATA: no saved state found in this file.")
            return False
        revision, state_json, updated_at = row
        try:
            state = json.loads(state_json)
        except Exception as e:
            print("APPLICATION DATA IS NOT READABLE: %s" % e)
            return False
        print("Last change saved: %s (revision %s)" % (updated_at, revision))
        print()
        print("Record counts in this file:")
        for key, label in (("inmates", "Inmates"), ("items", "Inventory items"),
                            ("requests", "Requests"), ("issues", "Issues"),
                            ("txns", "Stock transactions"), ("reminders", "Reminders"),
                            ("inventoryChecks", "Inventory checks")):
            value = state.get(key)
            print("  %-20s %s" % (label + ":", len(value) if isinstance(value, list) else "(missing)"))
            if not isinstance(value, list):
                ok = False
        try:
            audit_rows = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]
            print("  %-20s %s" % ("Change log entries:", audit_rows))
        except Exception:
            pass
        return ok
    finally:
        c.close()

def prune_backups():
    def old_files(prefix, keep):
        files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith(prefix) and f.endswith(".db"))
        for f in files[:-keep] if keep else files:
            os.remove(os.path.join(BACKUP_DIR, f))
    old_files("daily_", DAILY_KEEP)
    old_files("monthly_", MONTHLY_KEEP)

def run_backups_if_due():
    if not os.path.exists(DB_PATH):
        return
    today = datetime.date.today()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    daily = "daily_%s.db" % today.isoformat()
    if not os.path.exists(os.path.join(BACKUP_DIR, daily)):
        backup_now(daily)
    monthly = "monthly_%s.db" % today.strftime("%Y-%m")
    if not os.path.exists(os.path.join(BACKUP_DIR, monthly)):
        backup_now(monthly)
    prune_backups()

def backup_loop():
    while True:
        try:
            run_backups_if_due()
        except Exception as e:
            print("[backup] ERROR:", e)
        time.sleep(BACKUP_CHECK_SECONDS)

def initialize():
    migrate()
    load_state()
    try:
        run_backups_if_due()
    except Exception as e:
        print("Backup warning:", e)
    threading.Thread(target=backup_loop, daemon=True).start()

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "StateIssueV2/" + APP_VERSION
    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))

    def send_json(self, code, obj):
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        # API responses always reflect current shared state; only the static
        # page shell is eligible for offline caching by the service worker.
        path = urlparse(self.path).path
        if path == "/api/state":
            rev, state = load_state()
            self.send_json(200, {"rev": rev, "state": state}); return
        if path == "/api/ping":
            self.send_json(200, {"ok": True, "rev": load_state()[0], "version": APP_VERSION}); return
        if path == "/api/changes":
            q = parse_qs(urlparse(self.path).query)
            since = int(q.get("since", ["0"])[0])
            wait = min(float(q.get("wait", ["25"])[0]), 30.0)
            self.send_json(200, {"rev": wait_for_revision(since, wait)}); return
        if path == "/api/audit":
            self.send_json(200, {"rows": recent_audit()}); return
        if path == "/sw.js":
            if not os.path.exists(SW_PATH):
                self.send_error(404); return
            with open(SW_PATH, "r", encoding="utf-8") as f:
                raw = f.read().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Service-Worker-Allowed", "/")
            self.end_headers()
            self.wfile.write(raw)
            return
        if path in ("/", "/Stateissue.html"):
            rev, state = load_state()
            with open(HTML_PATH, "r", encoding="utf-8") as f:
                page = f.read()
            marker = "<script>window.__STATE_ISSUE_SERVER_STATE__=" + boot_json(rev, state) + ";</script>"
            page = page.replace("<script>", marker + "<script>", 1)
            raw = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        self.send_error(404)

    def do_POST(self):
        # Work queue posts use a narrow append operation; other edits use the
        # revision-checked full-state endpoint below.
        path = urlparse(self.path).path
        if path == "/api/messages":
            try:
                n = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(n).decode("utf-8"))
                who = payload.get("who", "")
                if not isinstance(who, str):
                    who = ""
                who = who[:40]
                rev, message, state = add_work_item(
                    payload.get("message"), self.client_address[0], who
                )
                self.send_json(200, {"ok": True, "rev": rev, "message": message, "state": state})
            except Exception as e:
                self.send_json(400, {"ok": False, "error": str(e)})
            return
        if path != "/api/state":
            self.send_error(404); return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            base_rev = int(payload["baseRev"])
            state = payload["state"]
            who = payload.get("who", "")
            if not isinstance(who, str):
                who = ""
            who = who[:40]
            if not isinstance(state, dict) or not isinstance(state.get("inmates"), list):
                raise ValueError("invalid state")
            ok, rev = save_state(base_rev, state, self.client_address[0], who)
            if not ok:
                self.send_json(409, {"ok": False, "rev": rev, "error": "CONFLICT"}); return
            self.send_json(200, {"ok": True, "rev": rev})
        except Exception as e:
            self.send_json(400, {"ok": False, "error": str(e)})

def main():
    initialize()
    with Server((HOST, PORT), Handler) as httpd:
        print()
        print("==============================================")
        print(" STATE ISSUE V%s - CONNECTED SERVER" % APP_VERSION)
        print("==============================================")
        print(" This computer:   http://127.0.0.1:%d" % PORT)
        print(" Other computers: http://%s:%d" % (local_ip(), PORT))
        print(" Database: %s" % DB_PATH)
        print(" Backups:  %s" % BACKUP_DIR)
        print()
        print("Keep this window running while State Issue is in use.")
        print("Press Ctrl+C to stop the server.")
        print()
        try:
            webbrowser.open("http://127.0.0.1:%d/" % PORT)
        except Exception:
            pass
        httpd.serve_forever()

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--verify":
        print()
        print("==============================================")
        print(" STATE ISSUE - CHECKING: %s" % sys.argv[2])
        print("==============================================")
        print()
        passed = verify_backup(sys.argv[2])
        print()
        print("RESULT: %s" % ("PASSED - this file is safe to use" if passed else "FAILED - do not use this file, try an older backup"))
        sys.exit(0 if passed else 1)
    try:
        main()
    except KeyboardInterrupt:
        # A deliberate Ctrl+C stop. Exit cleanly (code 0) so the launcher
        # script can tell this apart from a crash and NOT auto-restart it.
        print()
        print("Stopped.")
