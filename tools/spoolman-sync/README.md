# Spoolman Sync Tools

This directory contains tools for synchronizing the Filament Log app with Spoolman filament management system.

## Tools

### sync-filament-log-to-spoolman.py

Synchronizes filament inventory from the Filament Log app to Spoolman.

**Features:**
- Reads Filament Log export JSON data
- Creates matching vendors, filaments, and spools in Spoolman
- Maintains ID mapping between Filament Log and Spoolman
- Option to clear existing Spoolman data before sync

**Usage:**
```bash
python sync-filament-log-to-spoolman.py <filament_log_export.json> [--clear-spoolman]
```

**Example:**
```bash
python sync-filament-log-to-spoolman.py filament-log-backup-2026-09-22.json --clear-spoolman
```

**To export Filament Log data:**
1. Open http://3dworkshop.local/pages/filament-log.html
2. Click "Export backup" in the top right
3. Save the JSON file
4. Run the sync script with the file path

### auto-print-tracker.py

Polls a Moonraker (Klipper) or OctoPrint API for completed print jobs and writes
`pending-prints.json` for one-click import into the Filament Log web app.

**Features:**
- Detects completed prints automatically
- Converts printer job data to Filament Log v6 print objects
- Avoids duplicate entries with a `seen_ids` state file
- Optionally updates Spoolman spool `used_weight`
- Daemon mode for continuous polling

**Usage:**
```bash
python auto-print-tracker.py --config print-tracker-config.json --once
python auto-print-tracker.py --config print-tracker-config.json --daemon
```

**Setup:**
1. Copy `print-tracker-config.json.example` to `print-tracker-config.json` and edit it with your printer URL and API key
2. If using the home server, set `output_path` to `../../home-server/shared-storage/print-tracker/pending-prints.json`
3. Click **Auto prints** in the Filament Log Usage log tab to import detected prints
4. Set up a cron job or systemd timer to run the tracker in the background:
   ```bash
   # Example cron entry (polls every minute)
   * * * * * cd /path/to/tools/spoolman-sync && python auto-print-tracker.py --config print-tracker-config.json --once
   ```

### add-print-log.py

Adds print usage logs to both Filament Log and Spoolman systems.

**Features:**
- Adds usage records to both systems simultaneously
- Checks for duplicate entries before adding
- Uses ID mapping to match spools between systems
- Optional filament log file update

**Usage:**
```bash
python add-print-log.py --spool-id <filament_log_id> --amount <grams> --date <YYYY-MM-DD> --project "<project_name>" [--notes "<notes>"] [--filament-log <path_to_json>]
```

**Example:**
```bash
python add-print-log.py --spool-id CN1ihqTwxEKOZpW9SIDk --amount 76.76 --date 2026-09-18 --project "Batman Cat Helmet" --filament-log filament-log-backup-2026-09-22.json
```

## Workflow

### Initial Setup
1. Export your Filament Log data from the web app
2. Run the sync script to populate Spoolman with your inventory
3. The script creates a `spoolman_id_mapping.json` file for ID correspondence

### Adding Print Logs
1. Extract print information (from screenshots, printer logs, etc.)
2. Identify the correct spool ID from your Filament Log
3. Run the add-print-log script with the print details
4. The script checks for duplicates and adds to both systems

### Regular Maintenance
- Re-run the sync script after adding new spools to Filament Log
- Use the add-print-log script for each new print job
- Keep the `spoolman_id_mapping.json` file safe for future operations

## Files Generated

- `spoolman_id_mapping.json`: Maps Filament Log spool IDs to Spoolman spool IDs
- Backups: Original filament log exports are preserved

## Integration with Home Server

These tools are designed to work with the home server setup where:
- Filament Log app runs at http://3dworkshop.local
- Spoolman runs at http://spoolman.local
- Both services are behind nginx reverse proxy

## Requirements

- Python 3.6+
- requests library (`pip install requests`)
- Access to both Filament Log and Spoolman services