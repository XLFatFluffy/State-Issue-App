#!/usr/bin/env python3
"""Automated checks for the State Issue server. Run:  python test_server.py
Uses a temporary folder, so it never touches the real database."""
import os, sys, tempfile, json, threading, unittest, sqlite3, importlib.util, re
from html.parser import HTMLParser

TMP = tempfile.mkdtemp(prefix="si_test_")
os.environ["STATE_ISSUE_DATA"] = TMP
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("srv", os.path.join(HERE, "server.py"))
srv = importlib.util.module_from_spec(spec); spec.loader.exec_module(srv)

class T(unittest.TestCase):
    """Server tests use an isolated database and never touch live application data."""

    def setUp(self):
        # Each test starts from the same seeded state, so test order cannot
        # affect revisions, audit counts, or backup-file expectations.
        for f in os.listdir(TMP):
            p = os.path.join(TMP, f)
            if os.path.isfile(p): os.remove(p)
        import shutil
        shutil.rmtree(os.path.join(TMP, "backups"), ignore_errors=True)
        srv.migrate(); srv.load_state()

    def test_seed_file_exists_and_has_required_initial_state(self):
        with open(srv.SEED_PATH, "r", encoding="utf-8") as f:
            seed = json.load(f)
        for key in ("inmates", "requests", "requestItems", "issues", "txns", "items", "reminders", "inventoryChecks", "settings"):
            self.assertIn(key, seed)
        self.assertIsInstance(seed["inmates"], list)
        self.assertIsInstance(seed["items"], list)
        self.assertTrue(any(item.get("id") == "pants" for item in seed["items"]))

    def test_schema_version_recorded(self):
        c = sqlite3.connect(srv.DB_PATH)
        v = c.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0]
        c.close(); self.assertEqual(v, str(srv.SCHEMA_VERSION))

    def test_migrate_is_idempotent(self):
        srv.migrate(); srv.migrate()
        self.assertEqual(srv.load_state()[0], 0)

    def test_newer_database_refused(self):
        c = sqlite3.connect(srv.DB_PATH)
        c.execute("UPDATE schema_meta SET value='99' WHERE key='schema_version'"); c.commit(); c.close()
        with self.assertRaises(RuntimeError): srv.migrate()
        c = sqlite3.connect(srv.DB_PATH)
        c.execute("UPDATE schema_meta SET value='1' WHERE key='schema_version'"); c.commit(); c.close()

    def test_save_increments_revision(self):
        rev, st = srv.load_state()
        ok, r = srv.save_state(rev, st, "10.0.0.5")
        self.assertTrue(ok); self.assertEqual(r, 1)

    def test_stale_save_rejected(self):
        rev, st = srv.load_state()
        srv.save_state(rev, json.loads(json.dumps(st)), "a")
        ok, r = srv.save_state(rev, json.loads(json.dumps(st)), "b")
        self.assertFalse(ok); self.assertEqual(r, 1)

    def test_concurrent_writers_only_one_wins(self):
        rev, st = srv.load_state()
        res = []
        def w(n):
            s2 = json.loads(json.dumps(st)); s2["inmates"] = [{"id": str(n)}]
            res.append(srv.save_state(rev, s2, "x"))
        ths = [threading.Thread(target=w, args=(i,)) for i in range(40)]
        [t.start() for t in ths]; [t.join() for t in ths]
        self.assertEqual(sum(1 for r in res if r[0]), 1)
        self.assertEqual(srv.load_state()[0], 1)

    def test_audit_records_counts_not_names(self):
        rev, st = srv.load_state()
        st["inmates"] = [{"id": "i1", "first": "Secret", "last": "Person", "mdoc": "Z9"}]
        srv.save_state(rev, st, "10.0.0.7")
        row = srv.recent_audit(1)[0]
        self.assertEqual(row["workstation"], "10.0.0.7")
        self.assertIn("inmate records: 1 added", row["summary"])
        self.assertNotIn("Secret", row["summary"]); self.assertNotIn("Z9", row["summary"])

    def test_audit_counts_removed_and_changed(self):
        rev, st = srv.load_state()
        st["issues"] = [{"id": "I1", "qty": 1}, {"id": "I2", "qty": 2}]
        ok, r = srv.save_state(rev, st, "a")
        st2 = json.loads(json.dumps(st)); st2["issues"] = [{"id": "I1", "qty": 5}]
        srv.save_state(r, st2, "a")
        s = srv.recent_audit(1)[0]["summary"]
        self.assertIn("issues: 1 removed, 1 changed", s)

    def test_audit_records_who(self):
        rev, st = srv.load_state()
        srv.save_state(rev, st, "10.0.0.9", "Officer")
        row = srv.recent_audit(1)[0]
        self.assertEqual(row["who"], "Officer")

    def test_audit_who_defaults_to_blank(self):
        rev, st = srv.load_state()
        srv.save_state(rev, st, "10.0.0.9")
        row = srv.recent_audit(1)[0]
        self.assertEqual(row["who"], "")

    def test_backup_is_consistent_copy(self):
        rev, st = srv.load_state()
        srv.save_state(rev, json.loads(json.dumps(st)), "a")
        path = srv.backup_now("daily_test.db")
        c = sqlite3.connect(path)
        self.assertEqual(c.execute("SELECT revision FROM app_state").fetchone()[0], 1)
        c.close()

    def test_daily_and_monthly_backups_created_once(self):
        srv.run_backups_if_due(); srv.run_backups_if_due()
        files = os.listdir(srv.BACKUP_DIR)
        self.assertEqual(len([f for f in files if f.startswith("daily_")]), 1)
        self.assertEqual(len([f for f in files if f.startswith("monthly_")]), 1)

    def test_prune_keeps_limits(self):
        os.makedirs(srv.BACKUP_DIR, exist_ok=True)
        for i in range(40):
            open(os.path.join(srv.BACKUP_DIR, "daily_2000-01-%03d.db" % i), "w").close()
        for i in range(20):
            open(os.path.join(srv.BACKUP_DIR, "monthly_2000-%03d.db" % i), "w").close()
        srv.prune_backups()
        files = os.listdir(srv.BACKUP_DIR)
        self.assertEqual(len([f for f in files if f.startswith("daily_")]), srv.DAILY_KEEP)
        self.assertEqual(len([f for f in files if f.startswith("monthly_")]), srv.MONTHLY_KEEP)

    def test_messages_counted_in_audit_without_text(self):
        rev, st = srv.load_state()
        st["messages"] = [{"id": "M1", "from": "Officer", "to": "Worker", "text": "Secret note"}]
        srv.save_state(rev, st, "10.0.0.9")
        s = srv.recent_audit(1)[0]["summary"]
        self.assertIn("work queue items: 1 added", s)
        self.assertNotIn("Secret", s)

    def test_concurrent_work_items_get_unique_ids_and_are_all_saved(self):
        items = []
        lock = threading.Lock()

        def add(index):
            result = srv.add_work_item(
                {"title": "Work %d" % index, "body": "Details %d" % index},
                "workstation-%d" % index,
            )
            with lock:
                items.append(result[1]["id"])

        threads = [threading.Thread(target=add, args=(i,)) for i in range(12)]
        [thread.start() for thread in threads]
        [thread.join() for thread in threads]
        self.assertEqual(len(items), 12)
        self.assertEqual(len(set(items)), 12)
        rev, state = srv.load_state()
        self.assertEqual(rev, 12)
        self.assertEqual(len(state["messages"]), 12)

    def test_comments_counted_in_audit_without_text(self):
        rev, st = srv.load_state()
        st["comments"] = [{"id": "C1", "parentType": "inmate", "parentId": "i1",
                            "text": "Secret comment text", "author": "A", "at": "now"}]
        srv.save_state(rev, st, "10.0.0.9")
        s = srv.recent_audit(1)[0]["summary"]
        self.assertIn("comments: 1 added", s)
        self.assertNotIn("Secret", s)

    def test_comment_only_save_is_not_labeled_settings_only(self):
        rev, st = srv.load_state()
        st["comments"] = [{"id": "C1", "parentType": "inmate", "parentId": "i1",
                            "text": "hello", "author": "A", "at": "now"}]
        srv.save_state(rev, st, "10.0.0.9")
        s = srv.recent_audit(1)[0]["summary"]
        self.assertNotEqual(s, "settings only")

    def test_long_poll_wakes_on_save(self):
        import time
        rev, st = srv.load_state()
        result = {}
        def waiter():
            t0 = time.time(); result["rev"] = srv.wait_for_revision(rev, 10); result["secs"] = time.time() - t0
        th = threading.Thread(target=waiter); th.start()
        time.sleep(0.3)
        srv.save_state(rev, json.loads(json.dumps(st)), "x")
        th.join(12)
        self.assertEqual(result["rev"], 1)
        self.assertLess(result["secs"], 5)

    def test_long_poll_times_out_without_change(self):
        rev, _ = srv.load_state()
        import time
        t0 = time.time()
        self.assertEqual(srv.wait_for_revision(rev, 1.5), rev)
        self.assertGreaterEqual(time.time() - t0, 1.4)

    def test_boot_json_cannot_break_out_of_script(self):
        j = srv.boot_json(0, {"inmates": [{"notes": "</script><script>alert(1)</script>"}]})
        self.assertNotIn("</script>", j)
        self.assertEqual(json.loads(j)["state"]["inmates"][0]["notes"], "</script><script>alert(1)</script>")

    def test_realistic_state_round_trip_preserves_operational_edge_cases(self):
        """Mirror anonymized patterns from the supplied JSON backup, not its PII."""
        rev, state = srv.load_state()
        state["items"].append({"id": "item1008", "name": "Mat", "category": "Mat",
                                "sizes": ["A-new", "B-slight use"], "active": True})
        state["inmates"] = [{"id": "i1001", "mdoc": "L0427", "first": "Test",
                             "last": "Person", "status": "active", "zone": "A",
                             "sizes": {"pants": "2X - Black/White", "showershoes": "XXL"}}]
        state["requests"] = [{"id": "R1001", "inmateId": "i1001", "date": "2026-10-05",
                              "created": "2026-10-05T21:26:32.344Z", "type": "Officer",
                              "officer": "Test Officer", "notes": "state issue", "status": "partial"}]
        state["requestItems"] = [{"id": "RI1001", "requestId": "R1001", "itemId": "item1008",
                                  "size": "A-new", "qty": 2, "decision": "approved", "issuedQty": 1}]
        state["issues"] = [{"id": "I1001", "requestId": "R1001", "type": "Officer",
                            "inmateId": "i1001", "date": "2026-10-05", "itemId": "item1008",
                            "size": "A-new", "qty": 1, "reason": "Other"}]
        state["txns"] = [
            {"id": "T1001", "date": "2026-10-05", "itemId": "item1008", "size": "A-new",
             "qty": 10, "type": "Stock Received", "notes": "test stock receipt"},
            {"id": "T1002", "date": "2026-10-05", "itemId": "item1008", "size": "A-new",
             "qty": -1, "type": "Issue", "issueId": "I1001", "notes": "test issue"},
        ]
        state["reminders"] = [{"id": "RM1001", "type": "outstanding", "status": "open",
                               "inmateId": "i1001", "itemId": "item1008", "size": "A-new",
                               "qtyOwed": 1, "requestId": "R1001"}]
        state["inventoryChecks"] = [{"id": "IC1001", "date": "2026-10-05", "rows": [
            {"itemId": "item1008", "size": "A-new", "system": 9, "physical": 8, "diff": -1}],
            "differences": 1}]
        ok, newrev = srv.save_state(rev, state, "fixture")
        self.assertTrue(ok)
        loaded_rev, loaded = srv.load_state()
        self.assertEqual(loaded_rev, newrev)
        self.assertEqual(loaded["inmates"][0]["mdoc"], "L0427")
        self.assertEqual(loaded["items"][-1]["sizes"], ["A-new", "B-slight use"])
        self.assertEqual(loaded["requests"][0]["type"], "Officer")
        self.assertEqual(loaded["requestItems"][0]["issuedQty"], 1)
        self.assertEqual(loaded["txns"][1]["qty"], -1)
        self.assertEqual(loaded["reminders"][0]["qtyOwed"], 1)
        self.assertEqual(loaded["inventoryChecks"][0]["differences"], 1)

    def _start_http_server(self):
        httpd = srv.Server(("127.0.0.1", 0), srv.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(httpd.server_close)
        self.addCleanup(thread.join, 3)
        self.addCleanup(httpd.shutdown)
        return "http://127.0.0.1:%d" % httpd.server_address[1]

    def test_http_ping_reports_version_and_revision(self):
        import urllib.request
        base = self._start_http_server()
        with urllib.request.urlopen(base + "/api/ping", timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertTrue(body["ok"])
        self.assertEqual(body["version"], srv.APP_VERSION)
        self.assertEqual(body["rev"], 0)

    def test_http_state_endpoint_returns_seeded_state(self):
        import urllib.request
        base = self._start_http_server()
        with urllib.request.urlopen(base + "/api/state", timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertEqual(body["rev"], 0)
        self.assertIn("pants", [x["id"] for x in body["state"]["items"]])
        self.assertIsInstance(body["state"]["requests"], list)

    def test_http_post_saves_state_and_rejects_stale_revision(self):
        import urllib.request, urllib.error
        base = self._start_http_server()
        _, state = srv.load_state()
        payload = json.dumps({"baseRev": 0, "state": state, "who": "Worker"}).encode("utf-8")
        req = urllib.request.Request(base + "/api/state", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=3) as response:
            saved = json.loads(response.read().decode("utf-8"))
        self.assertEqual(saved["rev"], 1)
        stale = urllib.request.Request(base + "/api/state", data=payload,
                                       headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(stale, timeout=3)
        self.assertEqual(ctx.exception.code, 409)
        self.assertEqual(json.loads(ctx.exception.read().decode("utf-8"))["error"], "CONFLICT")
        ctx.exception.close()

    def test_http_post_rejects_invalid_state_shape(self):
        import urllib.request, urllib.error
        base = self._start_http_server()
        payload = json.dumps({"baseRev": 0, "state": {"inmates": "not-a-list"}}).encode("utf-8")
        req = urllib.request.Request(base + "/api/state", data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()

    def test_http_post_adds_work_item_and_returns_saved_state(self):
        import urllib.request
        base = self._start_http_server()
        payload = json.dumps({
            "message": {
                "title": "Coordinate pickup",
                "body": "Confirm the time with the team.",
                "author": "Worker",
                "created": "2026-10-22T14:00:00Z",
                "category": "Follow-up",
                "priority": "normal",
                "status": "open",
                "links": [],
                "comments": [],
            },
            "who": "Worker",
        }).encode("utf-8")
        req = urllib.request.Request(
            base + "/api/messages", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
        self.assertTrue(body["ok"])
        self.assertEqual(body["message"]["id"], "M1001")
        self.assertEqual(body["state"]["messages"][0]["title"], "Coordinate pickup")
        self.assertEqual(body["state"]["rev"], body["rev"])

    def test_http_post_rejects_empty_work_item(self):
        import urllib.request, urllib.error
        base = self._start_http_server()
        req = urllib.request.Request(
            base + "/api/messages",
            data=json.dumps({"message": {"title": "", "body": ""}}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=3)
        self.assertEqual(ctx.exception.code, 400)
        ctx.exception.close()

    def test_http_root_includes_bootstrap_and_no_store_header(self):
        import urllib.request
        base = self._start_http_server()
        with urllib.request.urlopen(base + "/", timeout=3) as response:
            page = response.read().decode("utf-8")
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
        self.assertIn("__STATE_ISSUE_SERVER_STATE__", page)
        self.assertIn('"rev":0', page)

    def test_service_worker_endpoint_is_served_without_cache(self):
        import urllib.request
        base = self._start_http_server()
        with urllib.request.urlopen(base + "/sw.js", timeout=3) as response:
            script = response.read().decode("utf-8")
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
            self.assertIn("javascript", response.headers.get("Content-Type", ""))
        self.assertIn("addEventListener", script)

    def test_backup_integrity_and_state_can_be_read_from_backup(self):
        rev, state = srv.load_state()
        state["items"].append({"id": "custom", "name": "Custom item", "category": "Linen",
                                "sizes": ["Used"], "active": True})
        ok, _ = srv.save_state(rev, state, "backup_test")
        self.assertTrue(ok)
        path = srv.backup_now("restore_test.db")
        c = sqlite3.connect(path)
        try:
            self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            row = c.execute("SELECT revision,state_json FROM app_state WHERE id=1").fetchone()
            self.assertEqual(row[0], 1)
            restored = json.loads(row[1])
            self.assertEqual(restored["items"][-1]["id"], "custom")
        finally:
            c.close()

    def test_verify_backup_passes_for_a_good_backup(self):
        rev, state = srv.load_state()
        ok, _ = srv.save_state(rev, state, "verify_test", "Officer")
        self.assertTrue(ok)
        path = srv.backup_now("verify_good.db")
        self.assertTrue(srv.verify_backup(path))

    def test_verify_backup_fails_for_a_missing_file(self):
        self.assertFalse(srv.verify_backup(os.path.join(srv.BACKUP_DIR, "does_not_exist.db")))

    def test_verify_backup_fails_for_a_corrupted_file(self):
        path = srv.backup_now("verify_corrupt.db")
        with open(path, "r+b") as f:
            f.seek(100)
            f.write(b"\x00" * 50)
        self.assertFalse(srv.verify_backup(path))

    def test_seed_and_backup_contract_preserve_optional_fields(self):
        """The real backup uses v3 export data; exercise its broad contract without PII."""
        with open(srv.SEED_PATH, "r", encoding="utf-8") as f:
            state = json.load(f)
        state.update({"version": 3, "seq": {"inmate": 1301, "request": 1062, "issue": 1296,
                                             "txn": 1437, "item": 1009, "ri": 1197,
                                             "inventoryCheck": 1001},
                      "requestItems": [], "issues": [], "txns": [], "deletions": [],
                      "reminders": [], "inventoryChecks": [], "messages": [],
                      "settings": {"lastBackup": None, "autoBackup": True, "backupRev": 0,
                                   "minStock": {}},
                      "_backup": {"app": "StateIssue", "created": "2026-10-09T08:19:00Z",
                                  "inmates": 0, "issues": 0, "txns": 0, "requests": 0,
                                  "reminders": 0, "inventoryChecks": 0}})
        self.assertEqual(state["version"], 3)
        for key in ("inmates", "items", "requests", "requestItems", "issues", "txns",
                    "reminders", "inventoryChecks", "settings", "seq", "_backup"):
            self.assertIn(key, state)
        self.assertEqual(state["_backup"]["txns"], len(state["txns"]))
        self.assertEqual(json.loads(json.dumps(state))["seq"]["inventoryCheck"], 1001)


class ClientSourceChecks(unittest.TestCase):
    """Static client checks catch regressions not covered by server/API tests."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "Stateissue.html"), "r", encoding="utf-8") as f:
            cls.html = f.read()

    def test_message_body_preserves_typed_line_breaks(self):
        # CSS preserves the message's original newlines without converting them
        # into HTML, keeping the text safe while retaining its formatting.
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn('esc(body)+"</div>"', compact)
        self.assertIn("white-space:pre-wrap", compact)

    def test_render_setup_populates_display_name_field(self):
        compact = re.sub(r"\s+", "", self.html)
        idx = compact.index("functionrenderSetup(){")
        body = compact[idx:idx + 500]
        self.assertIn('$("displayName")', body)
        self.assertIn("displayName()", body)

    def test_version_note_describes_connected_workstations_without_implying_access_control(self):
        self.assertIn("shared across connected workstations", self.html)
        self.assertNotIn("shared across authorized workstations", self.html)

    def test_display_name_is_local_to_each_workstation(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn('varDISPLAY_NAME_KEY="stateIssueWorkstationName"', compact)
        self.assertIn("localStorage.setItem(DISPLAY_NAME_KEY,name)", compact)
        idx = compact.index('$("saveDisplayName").onclick=function(){')
        body = compact[idx:idx + 700]
        self.assertIn("workstationDisplayName=name", body)
        self.assertNotIn("db.settings.displayName=name", body)

    def test_fixup_advances_all_id_sequences_from_existing_records(self):
        compact = re.sub(r"\s+", "", self.html)
        for source in (
            'inmate:{collection:"inmates",prefix:"i"}',
            'request:{collection:"requests",prefix:"R"}',
            'issue:{collection:"issues",prefix:"I"}',
            'txn:{collection:"txns",prefix:"T"}',
            'item:{collection:"items",prefix:"item"}',
            'ri:{collection:"requestItems",prefix:"RI"}',
            'reminder:{collection:"reminders",prefix:"RM"}',
            'inventoryCheck:{collection:"inventoryChecks",prefix:"IC"}',
            'message:{collection:"messages",prefix:"M"}',
            'comment:{collection:"comments",prefix:"C"}',
        ):
            self.assertIn(source, compact)
        self.assertIn(
            'Math.max(typeofcurrent==="number"&&isFinite(current)?current:1000,maxId,)',
            compact,
        )

    def test_backup_counts_and_checks_every_exported_collection(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn(
            "Object.keys(o).forEach(function(key){if(Array.isArray(o[key]))o._backup[key]=o[key].length;});",
            compact,
        )
        self.assertIn(
            'typeofb[key]==="number"&&(!Array.isArray(data[key])||b[key]!==data[key].length)',
            compact,
        )

    def test_automatic_backup_includes_inventory_catalog_changes(self):
        compact = re.sub(r"\s+", "", self.html)
        idx = compact.index("functionhasData(){")
        body = compact[idx:idx + 150]
        self.assertIn("Object.keys(db).some", body)
        self.assertIn("Array.isArray(db[key])&&db[key].length>0", body)

    def test_work_queue_record_links_are_searchable_and_require_a_match(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn('id="msgRequestLink"list="msgRequestOptions"', compact)
        self.assertIn('id="msgInmateLink"list="msgInmateOptions"', compact)
        self.assertIn('id="msgRequestOptions"></datalist>', compact)
        self.assertIn('id="msgInmateOptions"></datalist>', compact)
        self.assertRegex(
            self.html,
            r'r\.id\s*\+\s*" · "\s*\+\s*\(i\s*\?\s*i\.first\s*\+\s*" "\s*\+\s*i\.last',
        )
        self.assertRegex(
            self.html,
            r'i\.first\s*\+\s*" "\s*\+\s*i\.last\s*\+\s*" · "\s*\+\s*i\.mdoc\s*\+\s*" · "\s*\+\s*i\.id',
        )
        self.assertIn('dataListRecordId("msgRequestLink","msgRequestOptions")', compact)
        self.assertIn('dataListRecordId("msgInmateLink","msgInmateOptions")', compact)
        self.assertIn('if(requestSearch&&!rid)', compact)
        self.assertIn('if(inmateSearch&&!iid)', compact)

    def test_comments_and_work_queue_have_a_defined_datetime_formatter(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn("functionfmtDateTime(value){", compact)
        self.assertIn("date.toLocaleString()", compact)
        self.assertIn("esc(fmtDateTime(c.at))", compact)
        self.assertIn("esc(fmtDateTime(m.created||m.at))", compact)

    def test_messages_are_simple_threads_with_record_links(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn('id="msgText"', compact)
        self.assertIn('id="msgRequestLink"', compact)
        self.assertIn('id="msgInmateLink"', compact)
        self.assertIn('commentsHTML("message",m.id,true)', compact)
        self.assertIn('<detailsclass="card"><summary', compact)
        self.assertIn('buttonLabel=conversation?"SENDREPLY":"ADDCOMMENT"', compact)
        self.assertNotIn('id="msgSubject"', compact)
        self.assertNotIn('id="msgPriority"', compact)
        self.assertNotIn('id="msgCategory"', compact)
        self.assertNotIn("window.resolveMessage", compact)

    def test_work_item_post_falls_back_for_servers_without_message_endpoint(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn('if(r.status===404)returnpostViaState(3);', compact)
        self.assertIn('if(r.status===409&&retries>0)returnpostViaState(retries-1);', compact)
        self.assertIn('fetch("/api/state",{cache:"no-store"})', compact)

    def test_failed_async_state_save_restores_the_pre_change_state(self):
        compact = re.sub(r"\s+", "", self.html)
        self.assertIn("functionsave(rollbackState)", compact)
        self.assertIn("if(rollbackState){db=JSON.parse(rollbackState);db.rev=serverRev;renderAll();", compact)
        self.assertIn('if(saveBusy){toast("Waitforthecurrentsavetofinish,thentryagain.",true);returnfalse;}', compact)
        self.assertGreaterEqual(compact.count("if(messageSaving||saveBusy){"), 2)

    def test_html_has_one_real_body_and_no_duplicate_ids(self):
        class Structure(HTMLParser):
            def __init__(self):
                super().__init__()
                self.body_starts = 0
                self.body_ends = 0
                self.ids = []

            def handle_starttag(self, tag, attrs):
                if tag == "body":
                    self.body_starts += 1
                self.ids.extend(value for name, value in attrs if name == "id")

            def handle_endtag(self, tag):
                if tag == "body":
                    self.body_ends += 1

        structure = Structure()
        structure.feed(self.html)
        self.assertEqual(structure.body_starts, 1)
        self.assertEqual(structure.body_ends, 1)
        self.assertEqual(len(structure.ids), len(set(structure.ids)))

    def test_client_server_and_service_worker_versions_match(self):
        with open(os.path.join(HERE, "sw.js"), "r", encoding="utf-8") as f:
            worker = f.read()
        self.assertIn('var APP_VERSION = "' + srv.APP_VERSION + '"', self.html)
        self.assertIn("state-issue-shell-v" + srv.APP_VERSION, worker)

    def test_readme_changelog_has_a_real_blank_line(self):
        with open(os.path.join(HERE, "README.txt"), "r", encoding="utf-8") as f:
            readme = f.read()
        self.assertNotIn("\\nWHAT'S NEW", readme)

if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=1)
    sys.exit(0 if r.result.wasSuccessful() else 1)
