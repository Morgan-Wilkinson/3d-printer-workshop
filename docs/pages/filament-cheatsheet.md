# Filament Cheatsheet (Material Reference Guide)

**File:** `docs/pages/filament-cheatsheet.html` (~940 lines, self-contained)
**URL:** http://3dworkshop.local/pages/filament-cheatsheet.html
**Type:** Static reference document — no data storage beyond a theme preference

A material-selection guide: "what filament, for what part." Organized as a quick-compare table, a goal-based lookup, eight deep-dive material profiles, a decision grid, and a general good-to-know section. Complements `fdm-temp-speed-reference.html` — that page covers slicer settings; this one covers material choice.

---

## Contents

### Quick compare table

All eight materials sorted easiest → hardest to print, with columns: difficulty, strength, heat resistance, flexibility, UV/outdoor suitability, and whether an enclosure is needed. Designed for shortlisting before reading the full profile.

### "I want to make X → use Y" table

~20 goal-based lookups, e.g.:

| Project | Recommended |
|---|---|
| Miniatures / display models / first print | PLA |
| Electronics enclosure, jig, tool holder | PETG |
| Snap-fit clips | PETG (Nylon for heavy use) |
| Permanent outdoor mounts, signage | ASA |
| Automotive / near-heat housings | ABS or PC |
| Phone cases, grommets, straps, RC tires | TPU |
| Gears, hinges, repeated-stress parts | Nylon (PA/PA-CF) |
| Complex overhangs in one print | PVA or HIPS support |
| Clear high-heat lens/cover | PC (clear grade) |

### Material profiles

Eight cards (PLA, PETG, ABS, ASA, TPU, Nylon, PC, PVA & HIPS). Each has:

- **Tagline** — e.g. PLA "baseline material", ASA "ABS's outdoor sibling"
- **Spec grid** — nozzle temp, bed temp, fan, enclosure requirement, drying need
- **Strengths / Limits** — two-column pros & cons
- **Best for** — the one-line "when to reach for it"

Key guidance baked into the profiles:

- **PLA** — default pick; brittle and heat-sensitive (~55 °C softening)
- **PETG** — functional-part default; hygroscopic, strings, needs retraction tuning
- **ABS** — tough and vapor-smoothable; needs enclosure + ventilation, poor UV
- **ASA** — ABS's print process with excellent UV; the outdoor pick
- **TPU** — flexible; print slow, direct-drive preferred, very hygroscopic
- **Nylon** — best fatigue resistance; absorbs moisture within hours, warps hard
- **PC** — highest heat/impact; needs 270–310 °C nozzle and heated chamber
- **PVA & HIPS** — dissolvable supports; PVA (water) pairs with PLA/PETG, HIPS (limonene) pairs with ABS

### Decision cards ("Pick by what the part has to do")

Eight cards mapping the job to the material: looks good → PLA, handled/stressed → PETG, outdoors → ASA, near heat → ABS/PC, flexes → TPU, high fatigue → Nylon, one-piece overhangs → PVA/HIPS, clear + heat → PC.

### General good-to-know

Thirteen cross-material tips: moisture & storage, bed adhesion, stringing, cooling fan by material, nozzle wear (brass vs. hardened for filled filaments), ventilation/fumes, layer-height trade-offs, walls vs. infill for strength, part orientation relative to layer lines, calibration prints for new brands, unattended-print fire safety, and the "FDM isn't really food-safe" caveat.

---

## Technical details

- **Persistence:** none — the only `localStorage` key is `filament-guide-theme` (`dark`/`light`). Theme falls back to `prefers-color-scheme`.
- **Design:** dark warm-neutral palette, per-material accent dots (`--spool-*` variables), sticky jump-nav with anchor links, serif display font, print stylesheet.
- **Print-friendly:** `@media print` hides the nav and theme toggle, forces color-adjust exact so material colors survive printing.

## Maintenance notes

- All content is hand-authored HTML — adding a material means adding a compare-table row, a goal-table row (if applicable), a `.mat-card` section with a `--card-accent`, a jump-nav link, and optionally a decision card.
- Temps here are **generic starting points** (e.g. PLA 190–220 °C); for the X2D-calculated flow/speed numbers use `fdm-temp-speed-reference.html`.
- Footer caveat: brand-to-brand variation is real — always check the spool's spec sheet.
