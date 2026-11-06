# v32n-3 mechanism notes — topstepx-multi-v32 (v3.2)

Agent: v32n-3 · Dev partition 2010-06…2023-12 · Stressed costs: 2-tick slip + 1.5× fee
Experiments recorded: 3 evaluator screens (exp1 baseline sanity, exp2, exp3) + private
fill-sim triage of ~10 hypothesis families (documented below). No 200-seed null runs
(no candidate reached positive dev PnL, so none was frozen as finalist). No sealed-validation
submissions (no dev-eligible candidate; quota intentionally conserved).

## Support-systems finding (shared on feed)
- `ct_sec` wraps at midnight inside a session label (61200…86340 → 0…57540).
  `np.searchsorted` on a raw session slice is silently wrong. Python-level slicing by
  boolean time masks is required. Several early day-level screens were invalidated and re-run.

## Cost-ratio table (stressed RT cost per 1 micro contract / mean daily |open→close| $ per micro contract)
MNQ 2.6%, MYM 5.8%, MCL 6.2%, M2K 6.7%, MES 7.3%, MGC 12.0%, MHG 14.8%, M6E 26.6%.
Standard contracts are barred in practice by the $300-per-entry risk cap (e.g. 1 NQ with
a 15-pt stop = $300 → no room to survive 1-min noise). Micros are the only tradeable scale,
which caps aggregate exposure ~5 std-eq and pass math well below the $3000/30-session target.

## Hypothesis families screened (private next-open fill-sim at stressed costs, then evaluator where noted)
1. VWAP-band continuation (z = dev / mean-60bar-range, 30–120-min horizons): +0.1…+2.5 pt(s)
   per event gross in overlapping-window screens; event-study version ≤ +1.4 pt MNQ (t≈1.4),
   unstable per-year ⇒ below RT cost. Evaluator exp2 confirms (crash from own state-map bug
   fixed in later harness).
2. Quiet-morning pilot breakout + chandelier trail (exp2, evaluator): MES+MGC −60,003 dev
   PnL (MGC fee-bleed 4,714 entries; MES −3,571). Stop 0.9% of price vs ~1 pt capture legs.
3. Classic ORB (OR 09:30–10:00, ±15% buffer, OR-mid stop, 13:45 exit): 1-ct simulations
   −$0.2…−$6.8/day per symbol across MES/MNQ/MGC/MCL, all-years negative.
4. Quiet-OR afternoon ladder breakout w/ adds (exp3 evaluator, MNQ/MYM/M2K): −41,616 dev;
   47/278 winning days; win days up to +$1.4k but 231 losing days ~−$150 mean. Fees alone
   −$21.6k. Chandelier givebacks on stops exceed breakout captures.
5. First-2-minute fade (big |m2| → rest-of-day counter, 3×/6×rbar stops): −$0.2…−$10/day,
   all variants, all symbols (validated on corrected indexing).
6. Intraday momentum (first 30 min sign → last 30 min / last 3 h): −3…+2 bps, |t|≤2, dead
   after costs (re-verified post ct_sec fix).
7. Overnight drift segments (17:01→00:00 Asia, →07:30 Europe): +$1.7–5/day in 2019–2020,
   negative 2022–2023 ⇒ fails all-years-positive and is drift-beta besides.
8. RTH open→close long bias: negative 2019, 2020, 2022 in equity micros ⇒ not eligible.
9. NQ↔ES residual reversion (60-bar spread z-scores): fade mean ≈ −0.006…+0.035 z-units/60 min
   sign-flips by year; ≈1.4 bps ≈ $4/pair-60-min vs $11.5 pair-RT cost ⇒ dead.
10. Crude morning-trend persistence (MCL): +3…+5 bps t≈1, 2021+ only; $2-3/day per micro $6.25
    RT ⇒ dead. MGC last-30-min direction bias +1 bp t=2.7 < cost by 3×.

## Conclusion (dev only)
No tested causal 1-minute mechanism in the supplied CME roots clears stressed costs with
year-stable sign. The $300-per-entry risk cap + 5 std-eq aggregate + $1000 DLL/$2000 MLL +
$3000/30-session target implies a needed edge about an order of magnitude above anything
measured. No candidate frozen, none submitted for sealed validation (intentional: ineligible
submissions consume quota). If a future researcher finds a real edge, expect it in MNQ-sized
cheap-to-vol micros with multi-hour holding and ≤3 entries/day — everything faster is friction.

## Top candidate artifacts (none eligible; recorded for reference only)
- exp3 SHA256 15d973a982c3c944255d6c1e0f56e0de49a6f9ab05c8a8925af6904005062176 — quiet-OR
  ladder MNQ/MYM/M2K; least-bad win-tail geometry (best day +$1.4k), total −$41,616.
- exp2 SHA256 aa0e…(sample-clipped run) failed on implementation defect + thin economics.
- Baseline (provided) SHA256 aa0e04f6da85d1ed69ed0e1ba841df41205399a6d279eb615cbca5dbd0f435898.

## Reproduction
- Trusted evaluator: `python3 /opt/v32-eval/eval/sim.py --data /data/dev --symbols …
  --strategy "$PWD/strategy.py" --output … --null-seeds 0` (screens used 0 seeds throughout).
- All experiments logged in `experiments.jsonl`; each run committed, pushed via fork origin,
  and reported through `hive run submit`.
