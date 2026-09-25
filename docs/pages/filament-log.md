# Filament Log

**File:** `docs/pages/filament-log.html` (~3,900 lines, self-contained)
**URL:** http://3dworkshop.local/pages/filament-log.html
**Type:** Full application — inventory management, print logging, analytics

A filament and resin inventory manager that tracks what you own, what each print consumed, and what it all cost. Offline-first with `localStorage` persistence, optional Firebase cloud sync, and integrations with the home-server Price Monitor API and the auto print tracker.

---

## Views

The app is organized into four tabs plus a stats header row.

| Tab | Purpose |
|---|---|
| **Inventory** | Card grid of spools and refills with search, filters, sorting, and bulk operations |
| **Usage log** | Table of every logged print, sortable and filterable by spool |
| **Analytics** | Two-tier analysis: pre-built "Simple" dashboards and an "Advanced" JSON query builder |
| **Stats** | Summary charts — last 8 weeks of usage and breakdown by material |

### Stats header

Always visible above the tabs:

- **Spools on hand** — non-archived spool count
- **Refills** — non-archived refill count
- **Filament remaining** — total grams remaining across non-resin spools
- **Inventory value** — sum of `pricePaid × remaining%` (depreciated value)
- **Running low** — count of spools at or below their low-stock threshold

---

## Data model (v7)

Everything lives in three top-level arrays persisted to `localStorage`. Export format version is **7** (see [Version history](#version-history)).

### Spool

A complete filament spool (with housing) or a resin bottle.

```js
{
  id: "id…",                  // generated: "id" + timestamp36 + random
  type: "filament" | "resin",
  brand: "Bambu Lab",
  line: "PLA Basic",          // product line
  material: "PLA",            // drives build-plate compatibility
  colorName: "Jade White",
  colorHex: "#8a8f89",        // swatch used for the inventory ring

  // Filament only
  netWeightG: 1000,
  remainingG: 742,
  nozzleMin: 190, nozzleMax: 230,
  bedMin: 35, bedMax: 45,

  // Resin only
  netVolumeMl: 1000,
  remainingMl: 800,
  cureNotes: "2.5s normal, 30s base",

  // Purchasing
  pricePaid: 22.00,           // drives ALL cost calculations
  purchaseDate: "2026-09-01",
  purchaseSource: "Amazon",
  url: "https://…",           // product page, sent to price-api
  upc: "…",                   // UPC / ASIN / extracted product ID
  priceApiId: null,           // set after first successful price-api sync

  // Sale tracking
  originalPrice: 29.99,       // non-sale price; >0 marks item as "on sale"
  saleUnit: "kg" | "lb" | "spool" | "",
  bundleInfo: "5-pack",
  isSale: true,               // derived: originalPrice > 0

  lowStockPct: 15,            // threshold for "Running low" flag
  notes: "",
  archived: false             // archived items hidden everywhere
}
```

### Refill

A filament roll without spool housing. Nearly identical field set to a spool (minus `type`, `netWeightG`, `remainingG`), plus:

```js
{ amount: 1000 }  // grams on the roll
```

Refills are **independent** — they don't reference a spool. Editing a refill offers **Convert to spool**, which deletes the refill and creates a new spool with `netWeightG = remainingG = amount`.

### Print (v6 print-centric model)

One record per print job. Replaced the old v5 `usage` array.

```js
{
  id: "id…",
  project: "Gridfinity box",
  date: "2026-09-22",         // YYYY-MM-DD
  startTime: "2026-09-22T14:30" | null,   // datetime-local
  endTime: "2026-09-22T18:45" | null,
  buildPlate: "cool_plate" | "engineering_plate" | "texture_pei_plate" | "",
  plateName: "Plate 1 - Box Bottom",      // free-text plate identifier
  notes: "",
  loggedAt: "2026-09-22T19:00:00.000Z",   // ISO timestamp of log entry
  filaments: [
    { spoolId: "id…", amount: 142.5 }     // grams per spool; multi-spool prints supported
  ]
}
```

**Important:** logging a print decrements each spool's `remainingG`/`remainingMl` immediately (floored at 0). Deleting a print does **not** refund the material — the UI warns about this.

---

## localStorage keys

| Key | Contents |
|---|---|
| `filamentlog_spools` | Spool array |
| `filamentlog_refills` | Refill array |
| `filamentlog_prints` | Print array |
| `filamentlog_queries` | Saved advanced-analytics queries |
| `filamentlog_cloud` | Firebase config + sync code (if cloud sync enabled) |

`Store.persist()` writes all three data arrays on every mutation. If `localStorage` is full/unavailable it shows a toast warning.

---

## Reference data

### `FILAMENT_DB` — known-product presets (~65 entries)

Auto-fills brand, material, temps, and a reference price in the add-spool/refill/bulk-add forms. Rough street prices, always editable. Coverage:

- **Bambu Lab** — full lineup: PLA (Basic, Matte, Silk+, Tough+, Translucent, Aero, Sparkle, Metal, Marble, Galaxy, Wood, Glow, CF), PETG (HF, Translucent, CF), ABS/GF, ASA/CF, TPU (for AMS, 95A HF, 85A/90A), PC, PA6-CF/GF, PAHT-CF, PET-CF, PPA-CF, PPS-CF
- **Elegoo** — PLA variants, PETG (PRO/Rapid/Translucent/GF), TPU 95A, ABS, ASA, PC
- **Overture, eSUN, SUNLU, Hatchbox, Polymaker, Prusament** — common lines
- **Inland, Creality, ColorFabb, Fillamentum, NinjaTek** — misc
- **Resin** — Elegoo (Standard, ABS-Like, Water-Washable), Siraya Tech (Fast, Tenacious), Anycubic

### `BUILD_PLATES` — Bambu X2D build plates

Compatibility is **derived from `material`** (substring match against `compatibleMaterials`), never stored on the spool.

| ID | Name | Materials | Bed range |
|---|---|---|---|
| `cool_plate` | Cool Plate | PLA, PLA-CF, PETG, PETG-CF, TPU | 0–60 °C |
| `engineering_plate` | Engineering Plate | PLA, PLA-CF, ABS, ABS-GF, ASA, ASA-CF, Polycarbonate, Nylon-CF, Nylon-GF, PET-CF, PPA-CF, PPS-CF | 80–120 °C |
| `texture_pei_plate` | Textured PEI Plate | PLA, PLA-CF, PETG, PETG-CF, ABS, ASA, TPU | 0–100 °C |

Every spool card renders color-coded compatibility badges, the Inventory tab has a build-plate filter, the spool form live-updates compatible plates as you type a material, and each print log records which plate was used.

### `NOZZLES`

Only `standard_0.4` (0.4 mm) is defined — a placeholder for future nozzle tracking.

---

## Feature details

### Spool cards

- SVG ring showing `remainingG / netWeightG` percentage, colored by `colorHex`
- Metrics: remaining/total with unit (g or mL), $/kg, purchase source
- "~N days left at current pace" — computed by `estDaysRemaining()` from ≥2 print entries (total used ÷ days between first/last log)
- "Saved $X" line when `originalPrice > pricePaid`
- "Running low" flag at/below `lowStockPct`; "Nearly empty" (critical) at ≤5 %
- Checkbox for bulk selection → bottom action bar (Edit selected / Delete selected)

### Filters & sorting (Inventory)

Search across brand/line/color/material, material dropdown (populated from inventory), build-plate dropdown, sort by name/brand/source/price (default sorts emptiest-first), "Running low only" checkbox. Refills have their own search box.

### Bulk operations

- **Bulk add** — shared brand/material/temps/price/source, one row per color name + swatch
- **Bulk edit** — brand, material, source, price, low-stock threshold; blank fields keep existing values
- **Bulk delete** — via selection checkboxes

### Print logging

"Log a print" (per-spool button or Usage log tab) records project, date, plate name/number, build plate, start/end times, notes, and a **dynamic list of filaments** (spool + grams per row). Saving decrements each spool's remaining amount.

### Auto print tracker import

"Auto prints" button fetches `pending-prints.json` (default `/print-tracker/pending-prints.json`, configurable URL — written by `tools/spoolman-sync/auto-print-tracker.py`). Each pending print gets a checkbox, editable gram amounts, and a spool picker per filament. "Add selected" creates real print records (preserving the tracker's print ID to prevent re-import) and decrements spools. See the [tools README](../../tools/spoolman-sync/README.md).

### Price-API sync

- Every spool/refill save calls `syncToPriceApi()` → `POST` or `PUT http://price-api.local/api/products` with name, brand, category, url, upc, source, current_price, notes. The returned product ID is stored as `priceApiId` for subsequent PUTs.
- "↻ Sync prices" pushes all spools and refills silently.
- Failure is non-blocking (toast + console error) — the app still works if the API is down.

### Cloud sync (optional Firebase)

- Off by default; configured via "Cloud sync" modal with a **sync code** (shared namespace, treat like a password) and a pasted `firebaseConfig` object.
- Firestore path: `syncrooms/{code}/{spools|refills|prints}` with real-time `onSnapshot` listeners — all writes go straight to Firestore when connected.
- First connect to an empty sync room offers to upload existing local data, remapping spool IDs inside `print.filaments`.
- Disconnect reverts to the browser's local copy.

### Export / Import

- **Export** downloads `filament-log-backup-YYYY-MM-DD.json` (version 7).
- **Import** asks Replace (overwrite all) vs. Merge (append only new IDs), then runs migrations. Validates `spools` + `prints`/`usage` arrays exist.

### Analytics

- **Simple** — total spent, sale savings, breakdowns by source/material/brand/color, averages, top vendors; CSV export.
- **Advanced** — query builder: data source (all/spools/refills/prints), JSON filters (`{"brand":"Bambu Lab","pricePaid":{"$gt":20}}`), group-by (brand/material/color/source/month/year), aggregation (count, sum weight, sum/avg cost, avg weight, savings $, savings %), sorting, visualization (table, bar, pie, line). Queries can be named and saved to `filamentlog_queries`, reloaded, deleted; results export to CSV.

---

## Version history

`importJson` migrates older backups forward on import:

| Version | Change |
|---|---|
| v2 → v3 | Refills became independent (drops `spoolId`-linked refills) |
| v3 → v4 | Added sales fields (`originalPrice`, `saleUnit`, `bundleInfo`, `isSale`) |
| v4 → v5 | Refills gained full spool-parity fields; `isSale` auto-derived |
| v5 → v6 | `usage[]` (spool-centric) → `prints[]` (print-centric, `filaments[]` array) — also handled by `tools/spoolman-sync/migrate-v5-to-v6.py` |
| v6 → v7 | Added price-api fields (`url`, `upc`, `priceApiId`) |

Current export: `version: 7`.

---

## Architecture notes

- Single-file app: HTML + CSS + one IIFE-wrapped `<script>`; Firebase compat SDK (10.12.2) loaded from CDN for optional sync.
- `Store` object owns all state and CRUD; when `CloudSync.connected` is true, mutations write to Firestore and snapshots repopulate `Store` instead of touching local arrays directly.
- `Store.onChange` → `renderAll()` re-renders stats, grids, filters, and tables.
- IDs are `"id" + Date.now().toString(36) + random` — not stable across export/import merges (merge dedupes by ID).

## Known limitations

- Deleting a print doesn't restore filament to the spool (by design, with a warning).
- Deleting a spool orphans its `filaments[].spoolId` references — log rows render as "(deleted spool)".
- `priceApiId` survives edits but is lost if a spool is deleted and re-added.
- Sync-code "security" is namespace separation only — anyone with the Firebase config + code can read/write the room.
