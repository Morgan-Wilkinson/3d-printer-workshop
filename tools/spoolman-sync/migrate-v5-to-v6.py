#!/usr/bin/env python3
"""Migrate Filament Log v5 (usage array) to v6 (print-centric prints array)."""

import json
import re
from datetime import datetime, timezone

PRINT_LOGS = [
    {"project": "The best batman cat helmet ever!", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-18T15:49:00", "end": "2026-09-18T19:02:00",
     "filaments": [("Bambu PLA Black", 76.76)]},
    {"project": "Compact Poop Bin For X2D, P1S, P2S, X1C", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-18T19:39:00", "end": "2026-09-18T22:28:00",
     "filaments": [("Bambu PLA Grey", 149.02)]},
    {"project": "Filament Clip", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-18T23:11:00", "end": "2026-09-18T23:44:00",
     "filaments": [("Bambu PLA Green", 9.88)]},
    {"project": "Pixel 4 Leaf Clover Fidget", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-19T00:14:00", "end": "2026-09-19T04:53:00",
     "filaments": [("Bambu PLA Green", 59.98)]},
    {"project": "Everything Holder", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-19T10:54:00", "end": "2026-09-19T11:52:00",
     "filaments": [("Bambu PLA White", 25.74)]},
    {"project": "Japanese Samurai Incense Holder", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-19T12:22:00", "end": "2026-09-19T18:56:00",
     "filaments": [("Bambu PLA Black", 149.61)]},
    {"project": "Remote Control Caddy / Remote Control Holder", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-19T19:36:00", "end": "2026-09-19T22:19:00",
     "filaments": [("Bambu PLA Grey", 73.99)]},
    {"project": "Whale Fin Spoon Rest - Nautical", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-19T22:32:00", "end": "2026-09-20T01:44:00",
     "filaments": [("Bambu PLA Grey", 96.38)]},
    {"project": "Modern Desk Organizer", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-20T04:27:00", "end": "2026-09-20T09:10:00",
     "filaments": [("Bambu PLA Grey", 186.84)]},
    {"project": "Bambu Accessories Storage Toolbox P2S X2I H2S H2D", "plateName": "Plate 1 - Box Bottom", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-20T14:43:00", "end": "2026-09-20T16:10:00",
     "filaments": [("Bambu PLA Grey", 71.25)]},
    {"project": "Bambu Accessories Storage Toolbox P2S X2I H2S H2D", "plateName": "Plate 2 - box lid", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-20T16:17:00", "end": "2026-09-20T17:28:00",
     "filaments": [("Bambu PLA Grey", 43.37), ("Bambu PLA White", 1.38)]},
    {"project": "Sheridan mom and Dad", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-21T18:45:00", "end": "2026-09-21T19:36:00",
     "filaments": [("Bambu PLA White", 7.89)]},
    {"project": "Sheridan mom and Dad", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-21T20:14:00", "end": "2026-09-21T22:46:00",
     "filaments": [("Bambu PLA White", 41.92)]},
    {"project": "Custom Dog Pet Name Medal Tag", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-21T23:06:00", "end": "2026-09-21T23:26:00",
     "filaments": [("Bambu PLA Green", 3.04), ("Bambu PLA Black", 0.78), ("Bambu PLA White", 5.51)]},
    {"project": "The Scallop Shell Vase - Organic Coastal Decor", "plateName": "Plate 1", "buildPlate": "Textured PEI Plate",
     "start": "2026-09-21T23:29:00", "end": None,
     "filaments": [("Bambu PLA White", 85.54)]},
]

BUILD_PLATE_IDS = {
    "Cool Plate": "cool_plate",
    "Engineering Plate": "engineering_plate",
    "Textured PEI Plate": "texture_pei_plate",
}


def parse_time(s):
    if s:
        return s.replace(':', '')[:16] + ':' + s[-2:]
    return None


def normalize_project(p):
    return re.sub(r'\s+', ' ', p.strip().lower())


def main():
    with open('/Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22.json') as f:
        data = json.load(f)

    # Build a lookup from (material, color) to spool id for the colors used in the print logs
    spool_by_mat_color = {}
    for s in data.get('spools', []):
        key = (s['material'].lower().strip(), s['colorName'].lower().strip())
        spool_by_mat_color[key] = s['id']

    # Match each provided print log to a spool id and build print objects
    prints = []
    for log in PRINT_LOGS:
        filaments = []
        for name, amount in log['filaments']:
            # User labels are like "Bambu PLA Black", "Bambu PLA Grey and Bambu PLA White"
            parts = name.strip().lower().split()
            color = parts[-1]
            material = parts[-2] if len(parts) >= 2 else ""
            spool_id = spool_by_mat_color.get((material, color))
            if not spool_id:
                raise ValueError(f"Could not find spool for '{name}' (material={material}, color={color})")
            filaments.append({"spoolId": spool_id, "amount": amount})
        prints.append({
            "id": "id" + str(int(datetime.fromisoformat(log['start']).replace(tzinfo=timezone.utc).timestamp() * 1000)) + hex(hash(log['project']))[3:9],
            "date": log['start'][:10],
            "startTime": log['start'],
            "endTime": log['end'],
            "project": log['project'],
            "buildPlate": BUILD_PLATE_IDS.get(log['buildPlate'], log['buildPlate']),
            "plateName": log['plateName'],
            "notes": "",
            "filaments": filaments
        })

    data['prints'] = prints
    if 'usage' in data:
        del data['usage']
    data['version'] = 6
    data['migratedAt'] = datetime.now(timezone.utc).isoformat()

    with open('/Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22-v6.json', 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Migrated {len(prints)} prints to v6: /Users/morganwilkinson/Downloads/filament-log-backup-2026-09-22-v6.json")


if __name__ == "__main__":
    main()
