STATE ISSUE 3.3.0
Official operational release
=============================

State Issue is a browser-based application for tracking clothing and property
requests, inventory, issue history, and staff messages. One Windows computer
hosts the app and its shared database. Other computers connect to that host
through a trusted local network or VPN.

Version 3.3 adds three staff-set inmate review levels, color-coded profiles and
requests, and a combined request activity timeline. Version 3.2 added message
completion and deletion and shows linked messages on related records. Version
3.1 added the shared, structured feedback inbox in Setup. These features do not
add user accounts, role-based permissions, or a security certification.

Project repository:
https://github.com/XLFatFluffy/State-Issue-App

QUICK START
-----------
1. Put the complete project folder in a permanent location on the Windows host.
2. Run SETUP_NEW_COMPUTER.bat. It checks Python and runs the automated tests.
   Administrator permission is needed to configure Windows Firewall.
3. Run INSTALL_STATE_ISSUE_SERVICE.bat as administrator. The first service
   installation downloads the pywin32 dependency and therefore needs internet.
4. On the host, run START_STATE_ISSUE.bat. On each workstation, run
   OPEN_STATE_ISSUE.bat after connecting to the host network or VPN.

Read ADMIN_GUIDE.txt before putting operational data into the app. It covers
offline behavior, backups, recovery, updates, network access, and troubleshooting.

HOW IT WORKS
------------
- server.py serves Stateissue.html on TCP port 8787.
- Shared application data is stored in state_issue_v2.db, a SQLite database in
  the application folder by default. Set STATE_ISSUE_DATA to use a different
  data folder.
- The server makes daily and monthly SQLite backups in the backups folder
  while it is running. Keep a separate copy on another secure device.
- The host's localhost browser tab can work offline after it has loaded the app.
  Pending changes are stored in that browser and sync when the server returns,
  unless a concurrent edit creates a reconnect conflict that needs review.
- Workstations need the host network to load shared data and save changes. They
  cannot save while disconnected.
- The service worker caches only the application shell, not server-provided
  operational records.
- Normal use on the local network does not require internet access. Setup's
  optional Python installation, the first Windows service installation, and
  the automatic GitHub updater do require internet access.

FEATURES
--------
- Dashboard, inmate profiles, request review and fulfillment.
- Item and size catalog, inventory tracking, stock history, and low-stock alerts.
- Reports and CSV export.
- Shared messages with replies, completion and deletion controls, and optional
  links that also appear on the related request or inmate record.
- Comments, request snapshots, and an audit view of recent changes.
- Staff-set Routine, Needs review, and High risk inmate levels are color-coded
  on profiles and linked requests. Request activity brings together saved
  request snapshots, item issuance/voids, and comments in time order.
- Shared Setup inbox for detailed problem reports and improvement suggestions.
- JSON export/restore and automatic SQLite backups.

IMPORTANT LIMITATIONS
---------------------
- There are no user accounts, authentication, or per-user permissions. Anyone
  who can reach the app can view and change shared records.
- Workstation display names are optional, user-editable attribution labels;
  they do not identify or authenticate a person.
- Risk levels are staff-set review cues, not automatic decisions or a verified
  risk assessment. "Routine" means no additional flag is set, not that the
  inmate has never had an issue. Record factual reasons for review/high-risk.
- The server is intended for a trusted private network or VPN. Do not expose it
  directly to the public internet.
- CSV exports and database backups may contain sensitive personal information.
  Store them securely and limit access.
- An offline reconnect conflict is not merged automatically. The local copy is
  retained for review; save/export it and reconcile it against the server copy
  before discarding it.
- Problem reports and suggestions are shared with everyone who can access the
  app and are included in backups. Add a name or MDOC number when it helps
  identify the record involved.
- Automated tests cover the server, storage, HTTP behavior, and backup integrity.
  They do not replace manual testing of browser workflows or a verified restore.

TESTING
-------
Run from the project folder:

    python test_server.py

The tests use a temporary database and do not touch the operational database.
The application server uses Python's standard library. The optional Windows
service requires pywin32.

PROJECT FILES
-------------
ADMIN_GUIDE.txt                     Administrator operations and recovery.
CONNECT_AND_TROUBLESHOOT.txt        Connection steps and network diagnostics.
Stateissue.html                     Browser application.
server.py                           HTTP server, SQLite storage, audit, backups.
seed.json                           Initial data for a new database.
sw.js                               Host-browser offline application shell.
test_server.py                      Automated server and data-handling tests.
windows_service.py                  Windows service host.
SETUP_NEW_COMPUTER.bat              Host setup and pre-install checks.
INSTALL_STATE_ISSUE_SERVICE.bat     Install/start the Windows service.
UNINSTALL_STATE_ISSUE_SERVICE.bat   Remove the service; data is retained.
UPDATE_STATE_ISSUE.bat              Validated GitHub updater for the host.
VERIFY_BACKUP.bat                   Read-only SQLite backup verification.
START_STATE_ISSUE.bat               Open the app on the host via localhost.
OPEN_STATE_ISSUE.bat                Open the app from a workstation.

DATA SAFETY
-----------
Never replace or delete state_issue_v2.db when updating program files. Back up
the database before maintenance, verify backup files regularly, and follow
ADMIN_GUIDE.txt for restoration. Do not commit live databases, exports, or
backup files to the repository.
