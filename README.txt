STATE ISSUE — VERSION 2.4.4
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
- Inmates: inmate profiles, intake sizes, issue history, search, and comments.
- Requests: create and review item requests, record decisions, track partial
  fulfillment, and issue approved items.
- Inventory: manage the item catalog and sizes, record stock changes, review
  stock history, perform inventory checks, and track low-stock levels.
- Reports: review issue activity and export reports to CSV.
- Work Queue: create shared operational work items, set category and priority,
  search and filter, link requests or inmate records, comment, resolve, and reopen.
- Setup & Data: configure the optional display name and low-stock levels, review
  recent changes, export CSV data, manage items, and create or restore JSON backups.

Comments are available on inmate records, requests, individual issue records,
and work items. Comments do not change the operational status of their parent
record. A configured display name is stored as attribution for new comments and
work items; it is not a login or a verified identity.


HOW IT WORKS
------------
- `server.py` serves `Stateissue.html` and stores shared application state in
  `state_issue_v2.db` (SQLite). Application records are stored together as JSON
  state; the database also holds revisions and the change log.
- The server rejects stale full-state saves rather than silently overwriting a
  newer save. Work Queue submissions are appended by the server and receive
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
  who can access the application can see and change shared records. The display
  name is an attribution label only; do not treat it as proof of identity.
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
SETUP_NEW_COMPUTER.bat   Windows host setup.
INSTALL_STATE_ISSUE_SERVICE.bat  Install and start the Windows server service.
UNINSTALL_STATE_ISSUE_SERVICE.bat Remove the service without deleting data.
START_STATE_ISSUE.bat    Open State Issue on the host computer.
OPEN_STATE_ISSUE.bat     Windows shortcut for connecting workstations.

Keep the database and backup files safe. Do not delete or replace
`state_issue_v2.db` when updating program files.


VERSION 2.4.4 — OLDER SERVER COMPATIBILITY
------------------------------------------
- Work Queue posting falls back to the state-save API when the server does not
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
