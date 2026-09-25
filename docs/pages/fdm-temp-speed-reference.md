# FDM Temperature & Speed Reference

**File:** `docs/pages/fdm-temp-speed-reference.html` (~790 lines, self-contained)
**URL:** http://3dworkshop.local/pages/fdm-temp-speed-reference.html
**Type:** Static reference document — no data storage beyond a theme preference

A printer-side cheat sheet: starting-point slicer settings for nine filament types, followed by a symptom-first troubleshooting guide ("If X happens → change Y"). All speed/flow values are **calculated for the Bambu Lab X2D with the standard hotend** — max 40 mm³/s volumetric flow and 20,000 mm/s² acceleration — at 60–90% of rated maximum depending on the material.

---

## Contents

### Material spec cards

Nine materials, each as a card with a 13-field spec grid and a footnote with X2D-specific context. Values assume a stock 0.4 mm nozzle (brass or hardened steel); the spool's own spec sheet always wins.

| Material | Nozzle | Bed | Chamber | Max flow | Print speed | Accel | Notes |
|---|---|---|---|---|---|---|---|
| **PLA** | 200–220 °C | 50–60 °C | ambient | 24–36 mm³/s | 80–200 mm/s | 12–18k | Widest tolerance; high-speed capable |
| **PETG** | 230–250 °C | 70–85 °C | none, <45 °C | 20–30 mm³/s | 60–150 mm/s | 10–15k | Modest fan only — over-cooling weakens layer bond |
| **ABS** | 230–250 °C | 95–110 °C | 40–60 °C enclosed | 20–28 mm³/s | 60–120 mm/s | 8–12k | Lower accel deliberately — ringing/delamination prone |
| **ASA** | 235–255 °C | 95–110 °C | 45–60 °C enclosed | 20–28 mm³/s | 60–120 mm/s | 8–12k | Prints like ABS with UV stability |
| **TPU** (95A) | 210–230 °C | 30–60 °C | ambient | 8–12 mm³/s | 25–50 mm/s | 3–5k | Speed is the limit, not temp; direct drive recommended |
| **Nylon** (PA/PA-CF) | 250–270 °C (PA-CF 260–285) | 70–100 °C | 40–60 °C enclosed | 18–26 mm³/s | 50–100 mm/s | 6–10k | Most moisture-sensitive material listed |
| **PC** | 270–310 °C | 100–130 °C | 60–90 °C enclosed | 15–22 mm³/s | 40–80 mm/s | 4–7k | Hottest on the page; underheated PC delaminates |
| **PVA** | 190–210 °C | match main | none | 12–18 mm³/s | 40–70 mm/s | 6–10k | Support material; extremely hygroscopic |
| **HIPS** | 230–250 °C | 90–110 °C | 40–60 °C enclosed | 20–28 mm³/s | 60–120 mm/s | 8–12k | Limonene-soluble support; matches ABS temps |

Each card also lists: first-layer temp offset, part-cooling fan, retraction (Bowden **and** direct-drive as `distance @ speed`), first-layer speed, travel speed, and drying temp/duration.

### Troubleshooting section

Sixteen symptom cards. Each has an "applies to" tag and an ordered fix list — most likely/easiest first, with a one-line "why" under each fix. The doc's philosophy: change one thing at a time and reprint a small test piece.

1. **Stringing / wispy hairs** — dry filament → lower temp → more retraction → faster retraction → wipe/coast → faster travel
2. **Poor overhangs & sagging bridges** — more fan → slower overhang speed → lower layer height → cooler nozzle → supports below ~40–45°
3. **Under-extrusion at high speed** — raise temp → raise volumetric-flow cap → reduce speed → check for partial clog → check heater power on high-flow hotends
4. **Under-extrusion (general)** — verify diameter/E-steps → raise flow 2–5 % → raise temp → check gear tension/grinding → inspect nozzle
5. **Over-extrusion** — lower flow 2–5 % → re-check E-steps/diameter → lower temp → reduce line width
6. **Warping & lifting corners** — raise bed temp → enclose/eliminate drafts → brim → disable fan on first layers → clean bed → slow chamber cooldown
7. **Elephant's foot** — lower bed temp → reduce first-layer squish/Z-offset → slicer EF compensation → more first-layer cooling (PLA/PETG only)
8. **Poor first-layer adhesion** — IPA-clean bed → re-level/Z-offset → hotter first layer → slower first layer → adhesive → brim/raft
9. **Layer separation / delamination** — raise nozzle temp → less cooling → hotter chamber → dry filament → slower print → reorient part
10. **Zits & blobs at seams** — seam hiding/scarf seams → less retraction + wipe → coasting → lower flow
11. **Ringing / ghosting** — lower accel/jerk → lower speed → tighten belts → input shaping
12. **Layer shifting** — lower accel/speed → belts & pulley screws → physical obstructions → stepper current
13. **Nozzle clogs / heat creep** — dry filament → heatbreak cooling → avoid hot pauses → cold pull → check for worn nozzle (esp. after abrasives)
14. **Pillowing / top-surface gaps** — more top layers → denser/supportive infill → more top-layer cooling → slower top speed
15. **Popping / crackling sounds** — dry filament → sealed storage with desiccant → run a dryer during printing
16. **Cracking under load (engineering parts)** — hotter nozzle/chamber → reorient along layers → more walls vs. infill → dry filament → anneal

---

## Technical details

- **Persistence:** none — the only `localStorage` key is `fdm-ref-theme` (`dark`/`light`). Theme falls back to `prefers-color-scheme`.
- **Design:** same visual system as `filament-cheatsheet.html` — dark warm-neutral palette with per-material accent colors, sticky jump-nav, print stylesheet (`break-inside: avoid` on cards, nav/toggle hidden).
- **X2D specificity:** the intro callout states the flow/acceleration values are computed for the standard hotend (40 mm³/s, 20,000 mm/s²) and each footnote says what percentage of max the range represents and whether a high-flow hotend could push further.

## Maintenance notes

- Values are embedded directly in the HTML — updating a spec means editing the card markup.
- The doc invites expansion for additional hotends/printers ("Contact me to expand…"); a high-flow-hotend variant would roughly double the flow columns.
- Distinct from `filament-cheatsheet.html`: that page answers *which material to pick*; this one answers *what settings to start from and what to tweak when it fails*.
