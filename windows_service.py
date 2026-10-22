#!/usr/bin/env python3
"""Windows service host for the State Issue HTTP server. Requires pywin32."""
import os
import sys
import threading
import traceback

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import servicemanager
import win32event
import win32service
import win32serviceutil

import server


class StateIssueService(win32serviceutil.ServiceFramework):
    _svc_name_ = "StateIssueServer"
    _svc_display_name_ = "State Issue Server"
    _svc_description_ = "Hosts the State Issue application and shared database."

    def __init__(self, args):
        super().__init__(args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.httpd = None
        self.server_thread = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("State Issue Server is starting.")
        try:
            service_output = open(os.devnull, "w", encoding="utf-8")
            sys.stdout = service_output
            sys.stderr = service_output
            server.initialize()
            self.httpd = server.Server((server.HOST, server.PORT), server.Handler)
            self.server_thread = threading.Thread(
                target=self.httpd.serve_forever,
                kwargs={"poll_interval": 1},
                name="StateIssueHTTP",
            )
            self.server_thread.start()
            while True:
                result = win32event.WaitForSingleObject(self.stop_event, 1000)
                if result == win32event.WAIT_OBJECT_0:
                    break
                if not self.server_thread.is_alive():
                    raise RuntimeError("The State Issue HTTP server stopped unexpectedly.")
        except Exception:
            details = traceback.format_exc()
            servicemanager.LogErrorMsg("State Issue Server failed:\n" + details)
            raise
        finally:
            if self.httpd is not None:
                if self.server_thread is not None and self.server_thread.is_alive():
                    self.httpd.shutdown()
                    self.server_thread.join()
                self.httpd.server_close()
            servicemanager.LogInfoMsg("State Issue Server has stopped.")


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(StateIssueService)
