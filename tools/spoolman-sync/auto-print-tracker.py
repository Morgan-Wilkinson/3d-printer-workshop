#!/usr/bin/env python3
"""
Auto Print Tracker for Filament Log

Polls a 3D printer API (Moonraker / OctoPrint / Bambu LAN) for completed print jobs,
converts them to Filament Log v6 print objects, and writes pending-prints.json
for one-click import into the Filament Log web app.

Configuration:
    Copy print-tracker-config.json.example to print-tracker-config.json and edit it.

Usage:
    python auto-print-tracker.py --config print-tracker-config.json --once
    python auto-print-tracker.py --config print-tracker-config.json --daemon
"""

import argparse
import ftplib
import io
import json
import os
import re
import ssl
import socket
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Event

import requests


try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None


DEFAULT_CONFIG = {
    "printer_type": "moonraker",
    "url": "http://printer.local",
    "api_key": "",
    "serial": "",
    "access_code": "",
    "poll_interval": 60,
    "output_path": "pending-prints.json",
    "state_file": "print-tracker-state.json",
    "gcode_queue_path": "",
    "track_new_only": True,
    "spoolman_enabled": False,
    "spoolman_api": "http://spoolman.local/api/v1",
    "spoolman_spool_id": None
}

REQUEST_TIMEOUT = 20


class ImplicitBambuFTP(ftplib.FTP_TLS):
    """Implicit FTPS client for Bambu printers on port 990."""

    def __init__(self, context=None, *args, **kwargs):
        super().__init__(context=context, *args, **kwargs)
        self._bambu_context = context

    def connect(self, host='', port=0, timeout=-999, source_address=None):
        if host != '':
            self.host = host
        if port > 0:
            self.port = port
        if timeout != -999:
            self.timeout = timeout
        self.sock = socket.create_connection((self.host, self.port), self.timeout, source_address)
        self.af = self.sock.family
        self.sock = self.context.wrap_socket(self.sock, server_hostname=self.host)
        self.file = self.sock.makefile('r', encoding=self.encoding)
        self.welcome = self.getresp()
        return self.welcome

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn,
                                            server_hostname=self.host,
                                            session=self.sock.session)
        return conn, size


def strip_gcode(name):
    if not name:
        return "Unknown print"
    name = os.path.basename(name)
    for ext in (".gcode.3mf", ".gcode", ".g", ".bgcode", ".3mf"):
        if name.lower().endswith(ext):
            return name[: -len(ext)]
    return name


def parse_gcode_content(content):
    if not content:
        return [0.0]
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        return [0.0]

    total_match = re.search(r";\s*total filament used \[g\]\s*=\s*([\d.]+)", text, re.IGNORECASE)
    if total_match:
        return [float(total_match.group(1))]

    match = re.search(r";\s*filament used \[g\]\s*=\s*([\d.\s,]+)", text, re.IGNORECASE)
    if match:
        values = [float(v.strip()) for v in match.group(1).split(",") if v.strip()]
        if values:
            return values

    match = re.search(r";\s*filament used \[mm\]\s*=\s*([\d.\s,]+)", text, re.IGNORECASE)
    if match:
        values = [float(v.strip()) for v in match.group(1).split(",") if v.strip()]
        return [round(v / 1000 * 2.98, 2) for v in values]

    return [0.0]


def parse_3mf_content(data):
    if not data:
        return [0.0]
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            gcode_members = [m for m in zf.namelist() if m.lower().endswith(".gcode")]
            if gcode_members:
                return parse_gcode_content(zf.read(gcode_members[0]))
    except Exception:
        pass
    return [0.0]


def collect_ams_state(print_data):
    """Snapshot AMS tray remain% and weight, keyed by global tray index."""
    state = {}
    ams = print_data.get("ams") or {}
    for unit in ams.get("ams") or []:
        try:
            uid = int(unit.get("id", 0))
        except (TypeError, ValueError):
            uid = 0
        for tray in unit.get("tray") or []:
            try:
                tid = int(tray.get("id", 0))
            except (TypeError, ValueError):
                continue
            state[str(uid * 4 + tid)] = {
                "remain": float(tray.get("remain") or 0),
                "weight": float(tray.get("tray_weight") or 0),
            }
    for vt in ams.get("vt_tray") or []:
        try:
            tid = int(vt.get("id", 0))
        except (TypeError, ValueError):
            continue
        state[str(tid)] = {
            "remain": float(vt.get("remain") or 0),
            "weight": float(vt.get("tray_weight") or 0),
        }
    return state


def estimate_grams_from_ams(start_state, end_state):
    """Estimate grams used per tray from remain% deltas."""
    grams = []
    for key, start in (start_state or {}).items():
        end = (end_state or {}).get(key)
        if not end or not start.get("weight"):
            continue
        used = (start.get("remain", 0) - end.get("remain", 0)) / 100 * start["weight"]
        if used > 0:
            grams.append(round(used, 2))
    return grams


class PrintTracker:
    def __init__(self, config):
        self.config = {**DEFAULT_CONFIG, **config}
        self.state = self.load_state()

    def load_state(self):
        try:
            with open(self.config["state_file"], "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"seen_ids": [], "bambu": {"active_job": None}}

    def save_state(self):
        with open(self.config["state_file"], "w") as f:
            json.dump(self.state, f, indent=2)

    def load_pending(self):
        try:
            with open(self.config["output_path"], "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_pending(self, pending):
        out = Path(self.config["output_path"])
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(pending, f, indent=2)

    def get_moonraker_jobs(self):
        url = self.config["url"].rstrip("/") + "/api/history?limit=100"
        headers = {"Accept": "application/json"}
        if self.config.get("api_key"):
            headers["Authorization"] = "Bearer " + self.config["api_key"]
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {}).get("jobs", [])

    def get_octoprint_jobs(self):
        url = self.config["url"].rstrip("/") + "/api/job"
        headers = {
            "Accept": "application/json",
            "X-Api-Key": self.config["api_key"]
        }
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return [resp.json()]

    def get_grams_from_local_queue(self, subtask_name, gcode_file):
        queue = self.config.get("gcode_queue_path", "")
        if not queue or not Path(queue).is_dir():
            return [0.0]

        candidates = []
        if subtask_name:
            candidates.append(subtask_name)
        if gcode_file:
            candidates.append(strip_gcode(gcode_file))

        for root, _dirs, files in os.walk(queue):
            for filename in files:
                base = os.path.splitext(filename)[0]
                for candidate in candidates:
                    if candidate and (base.lower() in candidate.lower() or candidate.lower() in base.lower()):
                        path = os.path.join(root, filename)
                        try:
                            with open(path, "rb") as f:
                                data = f.read()
                            if filename.lower().endswith(".gcode.3mf") or filename.lower().endswith(".3mf"):
                                return parse_3mf_content(data)
                            return parse_gcode_content(data)
                        except Exception:
                            pass
        return [0.0]

    def download_bambu_gcode(self, remote_path):
        host = self.config["url"].rstrip("/").replace("https://", "").replace("http://", "")
        password = self.config.get("access_code", "")

        def ftp_open():
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ftps = ImplicitBambuFTP(context=ctx, timeout=20)
            ftps.connect(host, 990)
            ftps.login("bblp", password)
            ftps.prot_p()
            ftps.set_pasv(True)
            return ftps

        def try_retr(ftps, path):
            buffer = io.BytesIO()
            ftps.retrbinary(f"RETR {path}", buffer.write)
            return buffer.getvalue()

        try:
            ftps = ftp_open()
            name = remote_path
            # Try the full remote path; internal /data paths get stripped as fallbacks.
            alt = re.sub(r"^/?data/", "", name)
            for attempt in dict.fromkeys((name, alt, os.path.basename(name))):
                try:
                    data = try_retr(ftps, attempt)
                    ftps.quit()
                    return data
                except ftplib.error_perm:
                    pass
            ftps.quit()
        except Exception as e:
            print(f"Could not download Bambu gcode {remote_path}: {e}", file=sys.stderr)
        return None

    def get_grams(self, subtask_name, gcode_file):
        # 1. Try the local queue of sliced files first (most reliable)
        grams = self.get_grams_from_local_queue(subtask_name, gcode_file)
        if grams and any(g > 0 for g in grams):
            return grams

        # 2. Try to download from the printer's SD card / internal storage
        if gcode_file:
            data = self.download_bambu_gcode(gcode_file)
            if data:
                name = gcode_file.lower()
                if name.endswith(".gcode.3mf") or name.endswith(".3mf"):
                    return parse_3mf_content(data)
                return parse_gcode_content(data)

        return [0.0]

    def get_bambu_jobs(self):
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required for Bambu support. Install with: pip install paho-mqtt")

        host = self.config["url"].rstrip("/").replace("https://", "").replace("http://", "")
        port = 8883
        user = "bblp"
        password = self.config.get("access_code", "")
        serial = self.config.get("serial", "")
        if not host or not password or not serial:
            raise RuntimeError("Bambu config requires url, access_code, and serial")

        reports = []
        connected = Event()
        done = Event()

        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                client.subscribe(f"device/{serial}/report")
                client.publish(f"device/{serial}/request", json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}))
                connected.set()
            else:
                print(f"Bambu MQTT connect failed: {rc}", file=sys.stderr)
                done.set()

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                reports.append(payload)
            except Exception:
                pass

        def on_disconnect(client, userdata, *args):
            if not done.is_set() and not connected.is_set():
                done.set()

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            api = mqtt.CallbackAPIVersion.VERSION2
            client = mqtt.Client(callback_api_version=api,
                                 client_id=f"auto-print-tracker-{int(time.time())}")
        except AttributeError:
            client = mqtt.Client(client_id=f"auto-print-tracker-{int(time.time())}")

        client.tls_set_context(context)
        client.username_pw_set(user, password)
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        client.connect(host, port, 10)
        client.loop_start()

        connected.wait(timeout=10)
        if not connected.is_set():
            client.loop_stop()
            raise RuntimeError("Could not connect to Bambu MQTT broker")

        time.sleep(5)
        done.set()
        client.loop_stop()
        client.disconnect()

        finished = []
        bambu_state = self.state.setdefault("bambu", {})
        active = bambu_state.get("active_job")

        for report in reports:
            print_data = report.get("print", {})
            if not print_data:
                continue

            bambu_job_id = str(print_data.get("job_id", ""))
            gcode_state = str(print_data.get("gcode_state", "")).upper()
            gcode_file = print_data.get("gcode_file", "")
            subtask_name = print_data.get("subtask_name", "") or strip_gcode(gcode_file)

            running = gcode_state in ("RUNNING", "PREPARE", "PAUSE") or (gcode_state == "IDLE" and gcode_file and not active)

            if running and not active:
                bambu_state["active_job"] = {
                    "job_id": bambu_job_id,
                    "gcode_file": gcode_file,
                    "start_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                    "project": subtask_name,
                    "ams_state": collect_ams_state(print_data)
                }

            if active and (gcode_state in ("FINISH", "FAILED", "ABORT") or (gcode_state == "IDLE" and not gcode_file)):
                grams = self.get_grams(active.get("project") or subtask_name, active.get("gcode_file") or gcode_file)
                if not any(g > 0 for g in grams):
                    grams = estimate_grams_from_ams(active.get("ams_state"), collect_ams_state(print_data)) or grams
                active["end_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
                active["filament_grams"] = grams
                active["gcode_file"] = gcode_file or active["gcode_file"]
                active["project"] = subtask_name or active["project"]
                finished.append(active)
                bambu_state["active_job"] = None

        # Catch prints that were already finished before we started tracking
        for report in reports:
            print_data = report.get("print", {})
            gcode_state = str(print_data.get("gcode_state", "")).upper()
            gcode_file = print_data.get("gcode_file", "")
            subtask_name = print_data.get("subtask_name", "") or strip_gcode(gcode_file)
            bambu_job_id = str(print_data.get("job_id", ""))
            if (gcode_state in ("FINISH", "IDLE") and (gcode_file or subtask_name)):
                if not any(j.get("job_id") == bambu_job_id for j in finished) and bambu_job_id not in self.state.get("seen_ids", []):
                    grams = self.get_grams(subtask_name, gcode_file)
                    now = datetime.now(timezone.utc)
                    finished.append({
                        "job_id": bambu_job_id,
                        "gcode_file": gcode_file,
                        "start_time": now.strftime("%Y-%m-%dT%H:%M"),
                        "end_time": now.strftime("%Y-%m-%dT%H:%M"),
                        "project": subtask_name,
                        "filament_grams": grams
                    })

        self.state["bambu"] = bambu_state
        return finished

    def fetch(self):
        pt = self.config["printer_type"].lower()
        if pt == "moonraker":
            return self.get_moonraker_jobs()
        if pt == "octoprint":
            return self.get_octoprint_jobs()
        if pt == "bambu":
            return self.get_bambu_jobs()
        raise ValueError(f"Unsupported printer_type: {pt}")

    def normalize_moonraker(self, job):
        status = job.get("status", "completed")
        if status not in ("completed", "finished"):
            return None

        job_id = str(job.get("job_id"))
        if not job_id:
            return None

        start_ts = job.get("start_time")
        end_ts = job.get("end_time")

        start = start_ts and datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
        end = end_ts and datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")
        date = end_ts and datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime("%Y-%m-%d") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        filename = job.get("filename", "")
        project = strip_gcode(filename)
        filament_used = job.get("filament_used", 0)

        return {
            "id": f"print_{job_id}",
            "date": date,
            "startTime": start,
            "endTime": end,
            "project": project,
            "buildPlate": "",
            "plateName": "",
            "notes": f"Auto-detected from Moonraker: {filename}",
            "filaments": [{"spoolId": None, "amount": round(float(filament_used or 0), 2)}],
            "source": "moonraker",
            "jobId": job_id
        }

    def normalize_octoprint(self, job):
        job_info = job.get("job", {})
        file = job_info.get("file", {})
        filename = file.get("name", "")

        progress = job.get("progress", {})
        completion = progress.get("completion", 0)
        if completion and float(completion) < 100.0:
            return None

        filament = job_info.get("filament", {})
        total_mm = 0.0
        for tool, data in filament.items():
            if isinstance(data, dict):
                total_mm += float(data.get("length", 0) or 0)

        amount_g = round(total_mm / 1000 * 2.98, 2) if total_mm else 0.0

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        return {
            "id": f"print_{filename or now.replace(':', '').replace('-', '')}",
            "date": now[:10],
            "startTime": now,
            "endTime": now,
            "project": strip_gcode(filename) if filename else "Unknown print",
            "buildPlate": "",
            "plateName": "",
            "notes": f"Auto-detected from OctoPrint: {filename}" + (f" ({total_mm:.0f}mm filament)" if total_mm else ""),
            "filaments": [{"spoolId": None, "amount": amount_g}],
            "source": "octoprint",
            "jobId": filename or now
        }

    def normalize_bambu(self, job):
        project = job.get("project") or strip_gcode(job.get("gcode_file", ""))
        end = job.get("end_time", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"))
        date = end[:10]

        filaments = []
        for amount in job.get("filament_grams", [0.0]):
            if amount > 0:
                filaments.append({"spoolId": None, "amount": round(amount, 2)})
        if not filaments:
            filaments = [{"spoolId": None, "amount": 0.0}]

        return {
            "id": f"print_{job.get('job_id')}",
            "date": date,
            "startTime": job.get("start_time", ""),
            "endTime": end,
            "project": project,
            "buildPlate": "",
            "plateName": "",
            "notes": f"Auto-detected from Bambu: {job.get('gcode_file', '')}",
            "filaments": filaments,
            "source": "bambu",
            "jobId": job.get("job_id")
        }

    def normalize_print(self, raw):
        pt = self.config["printer_type"].lower()
        if pt == "moonraker":
            return self.normalize_moonraker(raw)
        if pt == "octoprint":
            return self.normalize_octoprint(raw)
        if pt == "bambu":
            return self.normalize_bambu(raw)
        return None

    def update_spoolman(self, amount_g, project):
        if not self.config.get("spoolman_enabled") or not self.config.get("spoolman_spool_id"):
            return
        spoolman_id = self.config["spoolman_spool_id"]
        api = self.config["spoolman_api"].rstrip("/")
        try:
            resp = requests.get(f"{api}/spool/{spoolman_id}", timeout=REQUEST_TIMEOUT)
            if resp.status_code != 200:
                print(f"Could not get Spoolman spool {spoolman_id}: {resp.status_code}", file=sys.stderr)
                return
            current = resp.json().get("used_weight", 0)
            update = requests.patch(f"{api}/spool/{spoolman_id}", json={"used_weight": current + amount_g}, timeout=REQUEST_TIMEOUT)
            if update.status_code in (200, 201):
                print(f"Updated Spoolman spool {spoolman_id}: +{amount_g}g for {project}")
            else:
                print(f"Failed to update Spoolman: {update.status_code}", file=sys.stderr)
        except Exception as e:
            print(f"Spoolman update error: {e}", file=sys.stderr)

    def poll(self):
        try:
            jobs = self.fetch()
        except Exception as e:
            print(f"Failed to fetch from {self.config['printer_type']}: {e}", file=sys.stderr)
            return

        pending = self.load_pending()
        seen = set(self.state.get("seen_ids", []))
        new = []

        for job in jobs:
            normalized = self.normalize_print(job)
            if not normalized:
                continue

            job_id = normalized.get("jobId")
            if job_id in seen and self.config.get("track_new_only", True):
                continue

            new.append(normalized)
            seen.add(job_id)

            if self.config.get("spoolman_enabled") and normalized["filaments"]:
                total = sum(f.get("amount", 0) for f in normalized["filaments"])
                if total:
                    self.update_spoolman(total, normalized["project"])

        if new:
            pending = new + pending
            self.save_pending(pending)
            self.state["seen_ids"] = list(seen)
            print(f"Added {len(new)} new print(s) to {self.config['output_path']}")
        else:
            print("No new completed prints found")
        self.save_state()

    def run_daemon(self):
        pt = self.config["printer_type"].lower()
        if pt == "bambu":
            self.run_bambu_daemon()
            return
        print(f"Auto print tracker running for {pt} at {self.config['url']}")
        while True:
            self.poll()
            time.sleep(self.config.get("poll_interval", 60))

    def run_bambu_daemon(self):
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required for Bambu support. Install with: pip install paho-mqtt")

        host = self.config["url"].rstrip("/").replace("https://", "").replace("http://", "")
        port = 8883
        user = "bblp"
        password = self.config.get("access_code", "")
        serial = self.config.get("serial", "")

        if not host or not password or not serial:
            raise RuntimeError("Bambu config requires url, access_code, and serial")

        connected = Event()

        def on_connect(client, userdata, flags, rc, properties=None):
            if rc == 0:
                client.subscribe(f"device/{serial}/report")
                client.publish(f"device/{serial}/request", json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}))
                connected.set()
                print(f"Connected to Bambu {serial} at {host}")
            else:
                print(f"Bambu MQTT connect failed: {rc}", file=sys.stderr)

        def on_message(client, userdata, msg):
            try:
                report = json.loads(msg.payload)
                self._handle_bambu_report(report)
            except Exception:
                pass

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        try:
            api = mqtt.CallbackAPIVersion.VERSION2
            client = mqtt.Client(callback_api_version=api,
                                 client_id=f"auto-print-tracker-{int(time.time())}")
        except AttributeError:
            client = mqtt.Client(client_id=f"auto-print-tracker-{int(time.time())}")

        client.tls_set_context(context)
        client.username_pw_set(user, password)
        client.on_connect = on_connect
        client.on_message = on_message

        client.connect(host, port, 60)
        client.loop_start()

        connected.wait(timeout=15)
        if not connected.is_set():
            client.loop_stop()
            raise RuntimeError("Could not connect to Bambu MQTT broker")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            client.loop_stop()
            client.disconnect()

    def _handle_bambu_report(self, report):
        print_data = report.get("print", {})
        if not print_data:
            return

        bambu_job_id = str(print_data.get("job_id", ""))
        gcode_state = str(print_data.get("gcode_state", "")).upper()
        gcode_file = print_data.get("gcode_file", "")
        subtask_name = print_data.get("subtask_name", "") or strip_gcode(gcode_file)

        bambu_state = self.state.setdefault("bambu", {})
        active = bambu_state.get("active_job")

        running = gcode_state in ("RUNNING", "PREPARE", "PAUSE") or (gcode_state == "IDLE" and gcode_file and not active)

        if running and not active:
            bambu_state["active_job"] = {
                "job_id": bambu_job_id,
                "gcode_file": gcode_file,
                "start_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                "project": subtask_name,
                "ams_state": collect_ams_state(print_data)
            }
            self.save_state()

        if active and (gcode_state in ("FINISH", "FAILED", "ABORT") or (gcode_state == "IDLE" and not gcode_file)):
            grams = self.get_grams(active.get("project") or subtask_name, active.get("gcode_file") or gcode_file)
            if not any(g > 0 for g in grams):
                grams = estimate_grams_from_ams(active.get("ams_state"), collect_ams_state(print_data)) or grams
            active["end_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            active["filament_grams"] = grams
            active["gcode_file"] = gcode_file or active["gcode_file"]
            active["project"] = subtask_name or active["project"]

            normalized = self.normalize_bambu(active)
            seen = set(self.state.get("seen_ids", []))
            if normalized["jobId"] not in seen:
                pending = self.load_pending()
                pending.insert(0, normalized)
                self.save_pending(pending)
                seen.add(normalized["jobId"])
                self.state["seen_ids"] = list(seen)
                print(f"Detected finished Bambu print: {active['project']} ({sum(grams)}g)")

                if self.config.get("spoolman_enabled") and grams:
                    self.update_spoolman(sum(grams), active["project"])

            bambu_state["active_job"] = None
            self.save_state()


def main():
    parser = argparse.ArgumentParser(description="Auto print tracker for Filament Log")
    parser.add_argument("--config", default="print-tracker-config.json", help="Path to config JSON")
    parser.add_argument("--once", action="store_true", help="Run one poll and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--dump-bambu", action="store_true", help="Dump Bambu MQTT reports for 10 seconds")
    args = parser.parse_args()

    try:
        with open(args.config, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        print("Creating default config file. Please edit it and run again.")
        with open(args.config, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    tracker = PrintTracker(config)

    if args.dump_bambu:
        dump_bambu_reports(config)
        return

    if args.daemon:
        tracker.run_daemon()
    else:
        tracker.poll()


def dump_bambu_reports(config):
    if mqtt is None:
        raise RuntimeError("paho-mqtt is required. Install with: pip install paho-mqtt")

    host = config["url"].rstrip("/").replace("https://", "").replace("http://", "")
    port = 8883
    user = "bblp"
    password = config.get("access_code", "")
    serial = config.get("serial", "")

    if not host or not password or not serial:
        raise RuntimeError("Bambu config requires url, access_code, and serial")

    connected = Event()
    count = [0]

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            client.subscribe(f"device/{serial}/report")
            client.publish(f"device/{serial}/request", json.dumps({"pushing": {"sequence_id": "0", "command": "pushall"}}))
            connected.set()
        else:
            print(f"Connect failed: {rc}", file=sys.stderr)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload)
            print(json.dumps(payload, indent=2))
            count[0] += 1
        except Exception:
            pass

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    try:
        api = mqtt.CallbackAPIVersion.VERSION2
        client = mqtt.Client(callback_api_version=api,
                             client_id=f"auto-print-tracker-{int(time.time())}")
    except AttributeError:
        client = mqtt.Client(client_id=f"auto-print-tracker-{int(time.time())}")

    client.tls_set_context(context)
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(host, port, 10)
    client.loop_start()

    connected.wait(timeout=10)
    if not connected.is_set():
        client.loop_stop()
        print("Could not connect", file=sys.stderr)
        return

    print("Listening for 10 seconds...")
    time.sleep(10)
    client.loop_stop()
    client.disconnect()
    print(f"Received {count[0]} report(s)")


if __name__ == "__main__":
    main()
