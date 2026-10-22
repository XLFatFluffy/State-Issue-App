STATE ISSUE — VERSION 2.4.4
CONNECTED BUILD (one host computer runs the server; other computers connect to it
over the local network — the host can be any computer on the network, not
necessarily an officer's)

For day-to-day running, backups and recovery, read ADMIN_GUIDE.txt.



WHAT'S NEW IN 2.4.3 — RELIABLE WORK QUEUE DELIVERY
---------------------------------------------------
- Work items now receive unique IDs and are appended atomically by the server,
  preventing simultaneous posts from different workstations from colliding or
  being rejected as stale full-state saves.
- The create form clears and reports success only after the server confirms the
  work item was saved. If sending fails, the entered text remains available to retry.
- Version and service-worker cache name bumped to 2.4.3.


WHAT'S NEW IN 2.4.4 — OLDER SERVER COMPATIBILITY
-------------------------------------------------
- Work item posting falls back to the existing state-save API if the server
  does not yet recognize the dedicated message endpoint. Revision conflicts
  are retried against the latest server state.
- Corrected the document body tag in the shipped page.
- Version and service-worker cache name bumped to 2.4.4.


WHAT'S NEW IN 2.4.2 — COMPLETE INVENTORY BACKUPS
-------------------------------------------------
- Automatic backups now recognize changes to the inventory catalog and other
  application collections, even when there are no inmates or stock transactions.
- Backup files record the number of entries in every exported collection, and
  restore checks those counts to detect missing or truncated data. Existing
  backups remain restorable.
- Version and service-worker cache name bumped to 2.4.2 so the host computer's
  browser loads the updated backup logic.


WHAT'S NEW IN 2.4.1 — FIXES TO THE 2.4.0 WORK QUEUE/COMMENTS FEATURES
-----------------------------------------------------------------------
- Fixed: line breaks typed into a work item's Details field were not shown when
  the item was displayed; the text ran together as one paragraph. Comments were
  not affected.
- Fixed: the Display Name field in SETUP did not show the currently saved name
  after a reload or on another workstation, even though the name was saved and
  in use. It now shows the saved name whenever SETUP is displayed.
- Fixed: the audit log in SETUP labeled a save as "settings only" when the only
  change was a new or edited comment, giving no indication a comment was added.
  Comments are now counted and labeled in the audit summary, and work queue
  items are labeled "work queue items" there instead of "messages".
- Version and service-worker cache name bumped to 2.4.1 so the host computer's
  browser does not keep the old cached application shell from 2.4.0.



WHAT'S NEW IN 2.4.0 — COMMENTS AND OPERATIONAL WORK QUEUE
---------------------------------------------------------
Purpose
- Replace the old Officer-to-Worker message exchange with a shared operational work queue.
  The earlier role selector assumed only two kinds of users and required people to label
  themselves as Officer or Worker. That was not the intended workflow: any participant
  may add a message or comment, so the app no longer uses those roles for messages.
- Add one configurable Display Name in SETUP. New messages and comments record that name
  and a timestamp. The name may be blank. Changing the setting affects new entries only;
  it does not rewrite historical attribution.
- This name is an attribution label, NOT authentication. There are no user accounts or
  verified identities; anyone with access can change the configured name.

Comments
- Comments are available on inmate records, requests, individual issue/issuance records,
  and message-board work items.
- Each comment stores its own ID, parent record type and ID, text, author name, and timestamp.
  Comments are separate from the underlying request/issue data, so adding a comment does not
  approve a request, issue inventory, or otherwise change operational status.
- Comments are shown in chronological order. A blank configured name is displayed as
  "Name not provided".
- Comments are preserved as part of the normal application state and therefore travel with
  the normal server saves and backups.

Operational message board
- The MESSAGES tab is now titled "Work Queue" inside the page. It creates work items with a
  required title, details, category, priority, creation time, author, and open/resolved status.
- Categories: State Issue, Request, Inventory, Follow-up, and General.
- Priorities: Low, Normal, High, and Urgent. The list uses a colored left edge and labels
  to make urgent/high-priority work easier to spot.
- Filters include open work (default), all/resolved status, priority, category, and text search.
- Work items can be linked to a request and/or an inmate record when created. Existing work
  items can add or replace a request/inmate link using LINK RECORD.
- Resolving an item keeps it in history and records resolution time, configured name, and
  optional resolution note. Resolved items can be reopened.
- Comments are available directly on each work item. Messages are not deleted by the UI.
- Older 2.3.0 messages are upgraded when the app reads the saved state. Existing message text,
  subject, sender, timestamp, and recipient fields are retained; old entries are presented
  through the new work-item fields. Because the old format represented messages as directed
  Officer/Worker messages, migrated entries retain their original sender as historical
  attribution and default to General / Normal / Open unless fields already exist.

Data compatibility and testing
- Added a comments collection and default settings.displayName field. Existing data is
  upgraded in memory by fixup() with empty comments and a blank display name when absent.
  The server stores the application state as a whole JSON state, so no SQLite schema migration
  was required for these new application-level fields.
- Increased the app/server version and service-worker cache name to 2.4.0 so browsers do not
  keep the old cached application shell.
- Automated server suite: all 30 existing tests passed after the changes.
- JavaScript syntax check passed with Node.js.
- Limitation: this environment could not validate the full interactive browser workflow.
  Manual acceptance testing is still required for creating comments on all four record types,
  creating/filtering/resolving/reopening messages, linking records, and restoring both old
  and new backups. The passing server tests do not prove every UI workflow works correctly.

Implementation choices and why
- One generic comments collection uses parentType + parentId rather than separate comment
  arrays on each record. This avoids copying comments into records, keeps the data model
  consistent, and lets comments follow a stable record ID.
- Work items link to stable request/inmate IDs rather than relying on names that can change.
- Completed messages are resolved rather than deleted so the board remains a useful record
  of work and its outcome.
- The implementation deliberately does not add private messages, user accounts, permissions,
  read receipts, or notifications. Those would add complexity without being required for this
  workflow, and a configured display name must not be mistaken for secure identity.

WHAT'S NEW IN 2.3.0
--------------------
- Added VERIFY_BACKUP.bat: drag a backup file onto it (or run it and type the path)
  to check the file is not damaged and see what's in it — last saved date, revision,
  and record counts — without changing anything.
- Added a matching "python server.py --verify <file>" check in server.py, with its
  own automated tests (3 new tests: a good backup, a missing file, a damaged file).
- This is the repeatable restore test called for in the implementation plan: running
  VERIFY_BACKUP.bat on the newest backup, regularly, confirms backups are actually
  usable without touching the live database. ADMIN_GUIDE.txt section 4 covers this;
  section 5 (actual restores) now points to it as a first step.
- Test result: all 30 automated tests passed.

WHAT'S NEW IN 2.2.0
--------------------
- Expanded automated tests from 18 to 27, including local HTTP API checks, stale-save
  conflict handling, malformed-state rejection, application bootstrap, service-worker
  delivery, realistic data round-tripping, and SQLite backup integrity.
- Reviewed the supplied State Issue JSON backup (exported 2026-10-09) to understand actual
  use patterns. Tests now include anonymized examples of Officer requests, partial issuance,
  custom item/size values, alphanumeric MDOC identifiers, negative issue transactions,
  outstanding reminders, and inventory-check differences. The original JSON and personal
  records are not included in this package.
- Bumped the app/server version and offline shell cache to 2.2.0 so clients do not retain
  the previous version's application shell.
- Updated this README and ADMIN_GUIDE.txt with the change record and test scope.

REVIEWED AND CORRECTED BEFORE RELEASE (Claude)
-----------------------------------------------
Before this package went out, it was checked line by line against the running app and
automated test suite, and two problems were found and fixed:
- SETUP_NEW_COMPUTER.bat had regressed to trying to install Python 3.12 via winget, which
  does not exist on Windows 7 and would leave the host computer stuck with no working
  Python. It now falls back to downloading and installing Python 3.8.10 directly (the same
  fix applied earlier for the Windows 7 host), the same way the previous working setup
  script did.
- sw.js (the offline helper) could hand the browser an empty response instead of a
  readable message if the host computer's very first load happened while the server was
  down. It now always falls back to the friendly "hasn't finished loading yet" message in
  that case, same as before this rewrite.
Everything else in this package — the test expansion itself, Stateissue.html, server.py,
and the rest of the documentation — was reviewed and is unchanged from what was supplied.

TEST SCOPE AND LIMITATIONS
--------------------------
The automated suite runs against a temporary data directory and does not touch the live
database. It tests server storage, revisions/conflicts, audit summaries, HTTP endpoints,
seed data, realistic state round-tripping, and SQLite backup integrity. It does NOT yet
automate clicking through every browser workflow (request approval, issue fulfillment,
stock adjustment, JSON restore, or offline reconnection). A headless-browser smoke test was
attempted during this release, but this runtime blocked navigation to its local test server;
that is an environment restriction, not a confirmed application failure, and no browser pass
is claimed. Those workflows still need browser/manual acceptance testing; do not treat the
passing server tests as proof that every UI workflow has been validated.

IMPLEMENTATION PLAN (APPROVAL-GATED)
------------------------------------
Development rule: each planned change is explained to the program owner first. Work on
that change begins only after explicit approval. After implementation, tests and results
are reported; the next change is proposed for approval. Preserve existing features and
protect the live database. Test data must be isolated from operational records.

BASELINE / CHANGE 1 — COMPLETED IN 2.1.2
- Inspect the current HTML, server, tests, README and administrator guide.
- Restore required release files missing from the supplied 2.1.1 archive:
  seed.json, sw.js, SETUP_NEW_COMPUTER.bat, START_STATE_ISSUE.bat and OPEN_STATE_ISSUE.bat.
- Confirm the seed data matches the application's built-in first-run defaults.
- Align application/server/documentation version labels.
- Result at the time: all 18 baseline automated tests passed.

CHANGE 2 — AUTOMATED TEST EXPANSION — COMPLETED IN 2.2.0
- Expanded tests from 18 to 27. Added API checks for ping/state/save/conflict and invalid
  payloads, bootstrap/service-worker delivery checks, realistic state round-trip coverage,
  and a SQLite backup integrity/read-back test.
- Reviewed the supplied JSON export to understand how the application is used. The data
  showed custom item IDs/categories/sizes, alphanumeric MDOC identifiers, Officer requests,
  partial/denied/approved statuses, linked request/issue/transaction records, negative stock
  transactions for issues, outstanding reminders, and inventory-check differences.
- Built anonymized fixtures for those patterns; the original backup and personal data are
  not embedded in the tests or release. No stricter normalization was added, because those
  values are legitimate parts of the existing workflow.
- Test result: all 27 automated tests passed.
- Remaining limitation: browser-level request/issue/inventory calculations and JSON restore
  are not covered by an automated browser harness yet; manual acceptance tests remain needed.

CHANGE 3 — BACKUP VERIFICATION AND A REPEATABLE RESTORE TEST — COMPLETED IN 2.3.0
(Approved by the program owner in chat before work began.)
- Added VERIFY_BACKUP.bat and "server.py --verify" so any backup file can be checked
  for damage and readability without touching the live database. Drag-and-drop, with
  a typed-path fallback, for the non-technical host computer.
- ADMIN_GUIDE.txt section 4 (verifying) and section 5 (restoring) rewritten; restoring
  now explicitly starts with verifying.
- 3 new automated tests cover a good backup, a missing file, and a damaged file.
- Test result: all 30 automated tests passed.

CHANGE 4 — COMMENTS AND OPERATIONAL WORK QUEUE — COMPLETED IN 2.4.0
(Explicitly approved by the program owner before implementation.)
- Added one optional Display Name setting, used for attribution on new comments and messages.
  Historical entries retain their stored attribution when the setting changes. This is not
  authentication, since the app has no accounts or verified identities.
- Added comments to inmate profiles, requests, individual issuance records, and work items.
  Comments have stable IDs, parent type/ID, text, timestamp, and optional author attribution.
- Replaced Officer/Worker directed messages with a shared operational work queue: title,
  details, category, priority, status, filters/search, request/inmate links, comments, and
  resolution/reopen behavior.
- Migrated old message fields in the application state at load time without discarding their
  original text, subject, sender, recipient, or timestamp. New fields receive safe defaults.
- Bumped app/server/service-worker cache version to 2.4.0 and updated README.txt and
  ADMIN_GUIDE.txt with scope, rationale, behavior, limitations, and acceptance-test guidance.
- Test result: all 30 existing automated server tests passed; JavaScript syntax and static
  UI checks passed. Browser navigation was blocked by this environment, so no browser-level
  workflow pass is claimed. Manual acceptance testing is still required before operational use.

NEXT PLANNED CHANGES — EACH REQUIRES OWNER APPROVAL BEFORE WORK BEGINS
5. Review and improve dashboard usability, including grouped reminders and clear alerts.
6. Review inmate lookup/profile workflows and recent-issue warnings.
7. Improve request fulfillment and outstanding-item tracking without duplicate issues.
8. Add useful inventory reports and a process for reviewing discrepancies.
9. Review simultaneous edits, stale data, offline sync conflicts and recovery behavior.
10. Review local-network security, exposure, and practical access controls for this environment.
11. Design any structured database migration as a separate, carefully tested project. No live
    database migration is to occur without explicit approval, backup, and a tested rollback plan.
12. Consider later operational additions such as printable issue receipts, stock receiving,
    and additional reports, based on the owner's priorities.
13. Perform final acceptance testing and package a clearly versioned release with an updated
    README, administrator guide, and change log.

The roadmap may be reordered if testing reveals a critical risk. Adding an item to this plan
is not authorization to implement it. The owner must approve each next change separately.

WHAT'S NEW IN 2.1.1
--------------------
Dashboard now has a "Today's Changes" board. It lists every change saved today,
with the time, the Officer/Worker role that was active on the computer that saved
it, and a plain-language count of what changed (no inmate or personal names — same
as the existing Recent Changes log in SETUP). It updates on its own as changes are
saved, on any computer, with no page reload needed. The Recent Changes log in
SETUP now also shows that role in a "Logged by" column.
For an update from 2.1.1, stop the server, make a separate copy of the whole program
folder (including state_issue_v2.db), then replace the program files from this package.
Do not overwrite or delete your live database. Restart START_STATE_ISSUE.bat. The
existing database upgrades itself automatically if needed. The package also restores
support files missing from the supplied 2.1.1 ZIP.

FILES IN THIS PACKAGE
---------------------
SETUP_NEW_COMPUTER.bat   Run ONCE on the host computer. Checks/installs Python if possible,
                         opens the network port, and runs the self-check.
START_STATE_ISSUE.bat    Starts the server on the host computer. Use this every day.
                         If it stops with an error it restarts itself automatically.
OPEN_STATE_ISSUE.bat     For other computers. Opens State Issue in the browser.
                         Edit the address inside it first.
VERIFY_BACKUP.bat        Checks a backup file is not damaged, without changing anything.
                         Drag a backup file onto it. See ADMIN_GUIDE.txt section 4.
Stateissue.html          The application (name never changes). Served by the server.
server.py                The server. Keep its window open while in use.
sw.js                    Lets the host computer keep working if the server stops
                         or the network drops. See "WORKING OFFLINE" below.
seed.json                Starting data, used only when the database is first created.
test_server.py           Automated checks (run by SETUP_NEW_COMPUTER.bat).
ADMIN_GUIDE.txt          Plain-language instructions for the administrator.
README.txt               This file.

DO NOT DELETE state_issue_v2.db. It is the central database. Backups are in the backups folder.

WORKING OFFLINE (host computer only)
-------------------------------------
The host computer — whichever one runs START_STATE_ISSUE.bat and opens State Issue
at the address shown as "This computer" in the server window — keeps working even
if the server program stops or the network drops. Changes made that way are saved
on that computer first (the status in the header turns orange: "Saved on this
computer — will sync") and are sent to the server automatically, with nothing lost,
as soon as it can be reached again.
Other computers are unchanged: if they cannot reach the server, they can see the
last data they loaded but cannot save until it is back.
This only works on the computer that opens State Issue at its OWN address
(what the server window calls "This computer"), never at the network address —
that is also how a web browser is allowed to let a page work offline at all, so
nothing needs to be turned on or configured for it.

WHAT CHANGED IN 2.1.0
----------------------
- The host computer (the one running the server) can now be any computer on the
  network, not specifically an officer's. Wording throughout now says "host
  computer" instead of "officer computer."
- The host computer keeps working if the server stops or the connection drops,
  and syncs automatically when it reconnects. See WORKING OFFLINE above.
- START_STATE_ISSUE.bat now restarts the server automatically if it stops with
  an error (up to 5 times in a row), instead of leaving State Issue down until
  someone notices and reopens the window.
- Minor fix: issuing an item against an outstanding-issue reminder is now
  protected against being recorded twice from a fast double-click, matching
  how issuing from a request already worked.

WHAT CHANGED IN 2.0.3
---------------------
- MESSAGES tab: a message board for the officer and the worker.
  Each computer chooses "This computer is used by: Officer or Worker". Messages go to the other role.
  Optional subject, up to 2000 characters, line breaks kept.
  New messages are marked NEW until the tab is opened on that computer. The tab shows a count,
  and the dashboard shows a notice.
  Messages are saved in the database, so they are backed up, appear in Recent Changes (as a count
  only), and update live on other computers.
- Messages cannot be deleted, so there is a permanent record.
- Privacy: there are no logins, so anyone at a computer can choose either role, and everyone can read
  every message. Do not use messages for anything that must be private from the worker.

WHAT CHANGED IN 2.0.2
---------------------
- Live updates: when anyone saves, every other open computer updates within about a second,
  with no refresh. Forms that someone is typing in are not replaced until they are closed.
- Setup and start batch files replace the old single start file. SETUP_NEW_COMPUTER.bat
  installs Python 3.12 if it is missing, opens port 8787 on private networks, and runs the self-check.
- The old computers do not need Python. They only need a browser and the address (see OPEN_STATE_ISSUE.bat).

WHAT CHANGED IN 2.0.1
---------------------
Fixes (from the 2.0.0 audit)
- The program now starts. In 2.0.0 the page failed to load on startup.
- Two computers saving at the same moment can no longer silently overwrite each other.
  The second save is refused and the user is told to reopen the program.
- Text typed into any field (for example, a note containing the characters "</script>")
  can no longer break the page or run code on other computers.
- If saved data cannot be read, saving is turned OFF so blank data cannot overwrite the real data.

New
- Automatic backups on the server: one per day (the last 30 days are kept) and one per month
  (the last 12 months are kept). Stored in the backups folder. Nothing needs to be pressed.
- Schema version: the database records its version and upgrades itself step by step on
  startup. The server refuses to run on a database made by a newer version.
- Audit log: every saved change is recorded with the date, time and the computer it came from,
  plus a count of what changed. It does not record names. It is shown in SETUP -> Recent Changes.
- Excel (CSV) export: SETUP -> Export to Excel gives Inmates, Issues, Stock History,
  Current Inventory and Requests. REPORTS -> EXPORT REPORT (CSV) exports the report on screen.
- Dashboard quick actions: FIND OR ADD INMATE, NEW REQUEST, ADD STOCK.
- Version number shown in the header and in SETUP.
- Automated tests (test_server.py) for saving, conflicts, audit, backups and escaping.

NOT IN THIS VERSION (deliberately)
- Logins, user accounts and permissions. Not needed for this site. The audit log identifies
  the computer, not the person, so use the Recent Changes list with that in mind.
- Normalized database tables. The data is still stored as one record per database. Splitting it
  into separate tables changes every screen, so it is planned as its own project.

UPGRADING (from 2.0.0 or 2.0.1)
--------------------
1. Stop the server window (Ctrl+C). On the new computer, double-click SETUP_NEW_COMPUTER.bat if it is a new install.
2. Copy the whole current folder somewhere safe, including state_issue_v2.db.
3. Replace the program files with the new ones. Keep state_issue_v2.db where it is.
   Delete START_STATE_ISSUE_V2.bat, which is replaced by START_STATE_ISSUE.bat.
4. Double-click START_STATE_ISSUE.bat. The database upgrades itself. Check the version in the header.
