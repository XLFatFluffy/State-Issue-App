STATE ISSUE — VERSION 2.5.1
============================

State Issue is a browser-based application for tracking inmate clothing and
property issues across a facility. One computer runs the server and holds the
shared database; other computers connect to it over the local network. The host
computer can be any computer on that network.

For installation, daily operation, backups, and recovery, see ADMIN_GUIDE.txt.
On the Windows host, INSTALL_STATE_ISSUE_SERVICE.bat installs the server as a
Windows service so it runs independently of an open terminal.


WHERE THE APP IS NOW
--------------------
The current build is a working, server-backed application with these operational
areas:

- Dashboard: at-a-glance requests needing decisions, approved requests awaiting
  issuance, low-stock items, reminders, and today's changes.
- Inmates: inmate profiles, intake sizes, issue history, search, comments, and
  a documented high-risk/review flag with a change history.
- Requests: create and review item requests, record decisions, track partial
  fulfillment, view request edit/decision snapshots, and issue approved items.
- Inventory: manage the item catalog and sizes, record stock changes, review
  stock history, perform inventory checks, and track low-stock levels.
- Reports: review issue activity and export reports to CSV.
- Messages: communicate on a shared board, reply in conversation threads, and link
  messages to requests or inmate records.
- Setup & Data: configure the optional workstation name and low-stock levels, review
  recent changes, export CSV data, manage items, and create or restore JSON backups.

Comments are available on inmate records, requests, and individual issue records.
Messages use threaded replies. Neither comments nor replies change the operational
status of their related record. Request snapshots retain the decision and item
details each time a request is created or updated. Issue records show the
workstation-specific display name and time of issuance when available. A configured
name is stored as attribution; it is not a login or a verified identity.


HOW IT WORKS
------------
- `server.py` serves `Stateissue.html` and stores shared application state in
  `state_issue_v2.db` (SQLite). Application records are stored together as JSON
  state; the database also holds revisions and the change log.
- The server rejects stale full-state saves rather than silently overwriting a
  newer save. Message submissions are appended by the server and receive
  unique IDs, including when several computers submit at once.
- Connected browsers receive live updates. The host computer can continue
  working offline when opened at its localhost address; its pending changes sync
  when the server becomes available. Other computers need the server to save.
- The server makes daily and monthly SQLite backups while it is running, keeping
  up to 30 daily and 12 monthly files. The browser also supports JSON export and
  restore. Verify a database backup read-only with
  `python server.py --verify <backup-file>`.
- The service worker caches only the application shell, not server-injected
  operational data. Offline use is limited to the host computer's localhost tab.


CURRENT LIMITATIONS
-------------------
- There are no user accounts, authentication, or per-user permissions. Anyone
  who can access the application can see and change shared records. Workstation
  names are attribution labels only; do not treat them as proof of identity.
- Officer and inmate-worker workflows have the same application permissions.
  This supports coverage when the officer is away, but it does not restrict
  sensitive actions or verify which staff member made a change.
- The server is intended for a trusted local network, not direct exposure to the
  public internet. Choose network access accordingly.
- If the host is offline, connected workstations can view their last loaded data
  but cannot save until the server is reachable. Offline changes made on the host
  can require manual review if they conflict with changes already saved elsewhere.
- Automated tests cover server storage, HTTP endpoints, revision conflicts,
  backup integrity and related data handling. They do not automate every
  interactive browser workflow. Manually test important workflows, especially
  request fulfillment, inventory operations, comments, work-item links, and
  backup/restore, before relying on them operationally.
- The application stores the operational collections in a single JSON state
  record rather than normalized relational tables.


TESTING
-------
Run the automated server tests from this folder:

    python test_server.py

The tests use an isolated temporary data directory; they do not use the
operational database. The HTTP server uses Python's standard library. The
optional Windows service host uses pywin32.


FILES
-----
Stateissue.html          Browser application.
server.py                Local-network server, database, audit log, and backups.
seed.json                Initial application state for a new database.
sw.js                    Offline application-shell cache for the host computer.
test_server.py           Automated server and data-handling tests.
ADMIN_GUIDE.txt          Installation and administrator operating instructions.
CONNECT_AND_TROUBLESHOOT.txt  Connection instructions and troubleshooting.
SETUP_NEW_COMPUTER.bat   Windows host setup.
INSTALL_STATE_ISSUE_SERVICE.bat  Install and start the Windows server service.
UNINSTALL_STATE_ISSUE_SERVICE.bat Remove the service without deleting data.
START_STATE_ISSUE.bat    Open State Issue on the host computer.
OPEN_STATE_ISSUE.bat     Windows shortcut for connecting workstations.

Keep the database and backup files safe. Do not delete or replace
`state_issue_v2.db` when updating program files.


VERSION 2.5.1 — WORKSTATION-SPECIFIC STAFF LABELS
-------------------------------------------------
- Display names are saved separately in each workstation's browser instead of
  as one shared setting, allowing officer and worker actions to carry different
  labels. Existing shared names are copied locally on first open.
- Names remain optional and unverified; this is not staff authentication.
- App, server, and service-worker cache versions are aligned at 2.5.1.

VERSION 2.5.0 — RISK FLAGS AND REQUEST HISTORY
----------------------------------------------
- Added a high-risk/review flag with a required factual reason, a visible alert
  in inmate/request/issuance workflows, and a history of flag changes.
- Added request creation/update snapshots showing decisions, reasons, quantities,
  and issued totals; earlier requests do not have retrospective snapshots.
- Added configured staff-name and timestamp attribution to new issuance records,
  including intake and outstanding-item issues.
- Kept officer and inmate-worker access equivalent; display names remain
  unverified, and the app still has no user accounts or role-based access.
- App, server, and service-worker cache versions were aligned at 2.5.0.

VERSION 2.4.5 — SIMPLE MESSAGE BOARD
-------------------------------------
- Simplified the Work Queue into a shared message board with direct replies.
- Removed required titles, categories, priorities, and resolve/reopen controls;
  request and inmate links remain available.
- Existing messages, replies, and linked records remain in the saved data.
- App, server, and service-worker cache versions are aligned at 2.4.5.

VERSION 2.4.4 — OLDER SERVER COMPATIBILITY
------------------------------------------
- Message posting falls back to the state-save API when the server does not
  recognize the dedicated message endpoint. Revision conflicts are retried
  against the latest server state.
- Corrected the document body tag in the shipped page.
- App, server, and service-worker cache versions are aligned at 2.4.4.

PREVIOUS 2.4.2–2.4.3 UPDATES
----------------------------
- Work items receive unique IDs and are appended atomically by the server.
  The create form reports success and clears only after the server confirms the
  save.
- Automatic backups detect changes to the inventory catalog and other
  collections, including changes made before any stock transactions.
- JSON backup files record collection counts, and restore checks those counts
  for missing or truncated data. Existing backups remain restorable.

VERSION 2.4.0–2.4.1 — COMMENTS AND WORK QUEUE
---------------------------------------------
- Replaced Officer/Worker-directed messages with a shared operational Work
  Queue. Older message data is migrated when the application reads saved state.
- Added comments to inmate records, requests, issue records, and work items.
- Added the optional Display Name setting for new comments and work items.
- Fixed display and audit-summary issues found after the initial release.
