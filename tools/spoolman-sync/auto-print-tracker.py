#!/usr/bin/env python3
"""
Auto Print Tracker for Filament Log

Polls a 3D printer API (Moonraker / OctoPrint) for completed print jobs,
converts them to Filament Log v6 print objects, and writes pending-prints.json
for one-click import into the Filament Log web app.

Configuration:
    Create print-tracker-config.json in this directory:
    {
      "printer_type": "moonraker",
      "url": "http://printer.local",
      "api_key": "",
      "poll_interval": 60,
      "output_path": "pending-prints.json",
      "state_file": "print-tracker-state.json",
      "track_new_only": true,
      "spoolman_enabled": false,
      "spoolman_api": "http://spoolman.local/api/v1",
      "spoolman_spool_id": null
    }

Usage:
    python auto-print-tracker.py --config print-tracker-config.json --once
    python auto-print-tracker.py --config print-tracker-config.json --daemon
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


DEFAULT_CONFIG = {
    "printer_type": "moonraker",
    "url": "http://printer.local",
    "api_key": "",
    "poll_interval": 60,
    "output_path": "pending-prints.json",
    "state_file": "print-tracker-state.json",
    "track_new_only": True,
    "spoolman_enabled": False,
    "spoolman_api": "http://spoolman.local/api/v1",
    "spoolman_spool_id": None
}

REQUEST_TIMEOUT = 20


class PrintTracker:
    def __init__(self, config):
        self.config = {**DEFAULT_CONFIG, **config}
        self.state = self.load_state()

    def load_state(self):
        try:
            with open(self.config["state_file"], "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"seen_ids": []}

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
        # OctoPrint does not have a public job history API without plugins.
        # Best source is /api/job for the currently active job.
        url = self.config["url"].rstrip("/") + "/api/job"
        headers = {
            "Accept": "application/json",
            "X-Api-Key": self.config["api_key"]
        }
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return [resp.json()]

    def fetch(self):
        pt = self.config["printer_type"].lower()
        if pt == "moonraker":
            return self.get_moonraker_jobs()
        if pt == "octoprint":
            return self.get_octoprint_jobs()
        raise ValueError(f"Unsupported printer_type: {pt}")

    def strip_gcode(self, name):
        if not name:
            return "Unknown print"
        name = os.path.basename(name)
        for ext in (".gcode", ".g", ".bgcode", ".3mf"):
            if name.lower().endswith(ext):
                return name[: -len(ext)]
        return name

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
        project = self.strip_gcode(filename)
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
        state = job.get("state", "").lower()
        # Only completed finished states; completed actual prints in OctoPrint are "Operational"
        # when idle, so we use the most recent job info and rely on end_time.
        job_info = job.get("job", {})
        file = job_info.get("file", {})
        filename = file.get("name", "")

        progress = job.get("progress", {})
        completion = progress.get("completion", 0)
        if completion and float(completion) < 100.0:
            return None

        # Filament data from OctoPrint is in mm. Convert to grams roughly using density 1.24 g/cm3
        # for PLA if only length is given. Keep things simple and store the raw mm in a note for now
        # but prefer a `weight` key when available.
        filament = job_info.get("filament", {})
        total_mm = 0.0
        for tool, data in filament.items():
            if isinstance(data, dict):
                total_mm += float(data.get("length", 0) or 0)

        # Very rough conversion: 1.75mm PLA/PETG ~ 2.98 g/m
        amount_g = round(total_mm / 1000 * 2.98, 2) if total_mm else 0.0

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
        return {
            "id": f"print_{filename or now.replace(':', '').replace('-', '')}",
            "date": now[:10],
            "startTime": now,
            "endTime": now,
            "project": self.strip_gcode(filename) if filename else "Unknown print",
            "buildPlate": "",
            "plateName": "",
            "notes": f"Auto-detected from OctoPrint: {filename}" + (f" ({total_mm:.0f}mm filament)" if total_mm else ""),
            "filaments": [{"spoolId": None, "amount": amount_g}],
            "source": "octoprint",
            "jobId": filename or now
        }

    def normalize_print(self, raw):
        pt = self.config["printer_type"].lower()
        if pt == "moonraker":
            return self.normalize_moonraker(raw)
        if pt == "octoprint":
            return self.normalize_octoprint(raw)
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
            self.save_state()
            print(f"Added {len(new)} new print(s) to {self.config['output_path']}")
        else:
            print("No new completed prints found")

    def run_daemon(self):
        print(f"Auto print tracker running for {self.config['printer_type']} at {self.config['url']}")
        while True:
            self.poll()
            time.sleep(self.config.get("poll_interval", 60))


def main():
    parser = argparse.ArgumentParser(description="Auto print tracker for Filament Log")
    parser.add_argument("--config", default="print-tracker-config.json", help="Path to config JSON")
    parser.add_argument("--once", action="store_true", help="Run one poll and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
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
    if args.daemon:
        tracker.run_daemon()
    else:
        tracker.poll()


if __name__ == "__main__":
    main()
