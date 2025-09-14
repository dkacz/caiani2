1. WHAT I CHANGED

- Removed GitHub Actions CI entirely and replaced CI-only guards with a local script `scripts/golden_guard.py`.
- Updated local docs to reflect the no-CI policy and how to run local guards.
- Synced the backlog to the new YAML (CI removed; local-only acceptance). 
- Kept `java_run_ok/java_error` meta fields as mandated; no oracle runner changes needed this round.

2. COMMANDS I RAN

- Inspected and removed CI:
  - `ls -la .github/workflows`
  - Deleted `.github/workflows/ci.yml`
- Searched and updated CI references in docs:
  - `rg -n "CI|Actions|badge|workflow" docs README.md -S`
  - Edited `docs/oracle_local_run.md`, `docs/java_wsl_setup.md`
- Added and exercised the local guard:
  - `python3 scripts/golden_guard.py` (fails as expected until real goldens exist without FALLBACK)

3. DIFFS (FULL DIFFS FOR MOST IMPORTANT CHANGES - CONDENSED FOR LESS IMPORTANT)

— FULL — Deletion of GitHub Actions

*** Begin Patch
*** Delete File: .github/workflows/ci.yml
*** End Patch

— FULL — scripts/golden_guard.py (new)

*** Begin Patch
*** Add File: scripts/golden_guard.py
#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


BASE_META = Path("artifacts/golden_java/baseline/meta.json")
BASE_SER = Path("artifacts/golden_java/baseline/series.csv")
FRONTIER_SER = Path("artifacts/golden_java/tax_theta1.5/series.csv")


def guard_no_fallback(meta_path: Path) -> None:
    if not meta_path.exists():
        print("skipped: golden baseline meta not found")
        return
    try:
        m = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"error: failed to read meta.json: {e}")
    raw = m.get("raw_sources", [])
    if any(isinstance(x, str) and x.startswith("FALLBACK:") for x in raw):
        raise SystemExit("guard failed: FALLBACK found in baseline raw_sources")
    print("ok: baseline raw_sources contains no FALLBACK markers")


def guard_gdp_diff(base_csv: Path, frontier_csv: Path) -> None:
    if not (base_csv.exists() and frontier_csv.exists()):
        print("skipped: baseline or frontier series not found")
        return
    b = pd.read_csv(base_csv)
    f = pd.read_csv(frontier_csv)
    wb = b[(b["t"] >= 501) & (b["t"] <= 1000)]["GDP"].mean()
    wf = f[(f["t"] >= 501) & (f["t"] <= 1000)]["GDP"].mean()
    if pd.isna(wb) or pd.isna(wf):
        raise SystemExit("guard failed: empty window means for GDP")
    if abs(float(wb) - float(wf)) <= 1e-12:
        raise SystemExit("guard failed: frontier equals baseline GDP mean — placeholder suspected")
    print("ok: GDP means differ between baseline and tax_theta1.5")


def main() -> int:
    guard_no_fallback(BASE_META)
    guard_gdp_diff(BASE_SER, FRONTIER_SER)
    return 0


if __name__ == "__main__":
    sys.exit(main())

*** End Patch

— CONDENSED — docs/oracle_local_run.md, docs/java_wsl_setup.md, docs/backlog.md updated to remove CI references and sync backlog to the local-only YAML.

4. ARTIFACTS PRODUCED/UPDATED

- Deleted: `.github/workflows/ci.yml`
- Added: `scripts/golden_guard.py`
- Updated: `docs/oracle_local_run.md`, `docs/java_wsl_setup.md`, `docs/backlog.md`

5. RESULTS / CHECKS

- `python3 scripts/golden_guard.py` currently reports:
  - `guard failed: FALLBACK found in baseline raw_sources` (expected until we generate real goldens locally).
- Docs now reference local guards; no CI files remain in the repo.

6. ISSUES & BLOCKERS

- Real seeded Java goldens (baseline + frontiers) must be generated locally using a valid `S120_ORACLE_CLASSPATH` and main model XML path. Without them, guards fail as designed and parity remains pending.

7. UPDATED BACKLOG (full YAML INLINE - NEW, CI DROPPED)

```yaml
- id: M1
  title: Milestone – Engine ready (sfctools skeleton, scheduler, MC)
  rationale: Deterministic SFC engine with the 19-step loop, artifacting, diagnostics.
  paper_refs:
    - {section: "Sequencing & accounting discipline", page: null, eq_or_fig_or_tab: "19-step; FlowMatrix"}
  deps: []
  instructions: FlowMatrix glue; 19-step scheduler; seeds & MC runner.
  acceptance_criteria: "FlowMatrix checks pass at steps 3/7/12/16/19; local smoke run creates non-empty CSVs."
  artifacts_expected: ["artifacts/smoke/.csv"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: M2
  title: Milestone – Baseline parity vs Java
  rationale: Match baseline macro & inequality dynamics to oracle within tolerances.
  paper_refs:
    - {section: "Baseline & validation window", page: null, eq_or_fig_or_tab: "t=501–1000; macro panels"}
  deps: ["M1", "T-ORACLE-RUN-FRONTIERS", "T-GOLDEN-BASELINE", "T-BL-SLICE1", "T-BL-SLICE2", "T-BL-SLICE3-EXT"]
  instructions: Implement baseline behaviors and compare to Java golden CSVs (baseline).
  acceptance_criteria: "MC means (t=501–1000) for GDP, C, I, INFL, UNEMP, PROD_C within ±10% of oracle; co-movements preserved; inequality paths qualitatively consistent."
  artifacts_expected: ["artifacts/golden_java/baseline/.csv", "artifacts/python/baseline/.csv", "reports/baseline_parity.md"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: M3
  title: Milestone – Experiments parity (θ & tu sweeps)
  rationale: Replicate direction and relative magnitudes for policy grids.
  paper_refs:
    - {section: "Policy experiments", page: null, eq_or_fig_or_tab: "Progressive tax θ; wage rigidity tu"}
  deps: ["M2", "T-GOLDEN-EXPTS"]
  instructions: Implement θ- and tu-sweeps; compute MC averages (t=501–1000); compare Δ vs baseline.
  acceptance_criteria: "Signs & ordering match; |Δ| errors ≤10% vs oracle; Lorenz/Gini patterns qualitatively consistent."
  artifacts_expected: ["artifacts/experiments/tax_sweep/", "artifacts/experiments/wage_sweep/", "reports/experiments_parity.md"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: T-SKEL
  title: Project skeleton on sfctools + param registry
  rationale: Parameterization mirrors Appendix A table to avoid drift.
  paper_refs:
    - {section: "Appendix A", page: null, eq_or_fig_or_tab: "Table 1 – Parameters"}
  deps: ["M1"]
  instructions: Registry loads/validates defaults; include χ, ε, ν, μ₀, θ, tu, rates, thresholds per Table 1.
  acceptance_criteria: "params_default.yaml keys/values match Table 1; tests pass locally."
  artifacts_expected: ["s120_inequality_innovation/config/params_default.yaml", "tests/test_params.py"]
  repo_paths_hint: ["s120_inequality_innovation/config", "s120_inequality_innovation/core/registry.py"]
  estimate: M

- id: T-SCHED
  title: 19-step scheduler scaffold + FlowMatrix checks
  rationale: Enforce exact order of events and accounting cut-points.
  paper_refs:
    - {section: "Sec. 2.1", page: null, eq_or_fig_or_tab: "19-step sequence"}
  deps: ["T-SKEL"]
  instructions: Scheduler invokes step stubs; SFC checks after steps 3/7/12/16/19.
  acceptance_criteria: "Unit test enumerates 19 labels; local SFC smoke passes."
  artifacts_expected: ["tests/test_scheduler_19steps.py", "artifacts/smoke/timeline.csv"]
  repo_paths_hint: ["s120_inequality_innovation/core/scheduler.py", "s120_inequality_innovation/core/flowmatrix_glue.py"]
  estimate: M

- id: T-MC
  title: Monte Carlo runner + seed management + artifact foldering
  rationale: Reproducibility for baseline/experiments; fixed streams.
  paper_refs:
    - {section: "Simulation setup", page: null, eq_or_fig_or_tab: "1000 periods; 25 reps"}
  deps: ["T-SCHED"]
  instructions: Named RNG streams; per-run artifacts; aggregated stats.
  acceptance_criteria: "25-run baseline executes locally; seeds logged; summary exists."
  artifacts_expected: ["artifacts/baseline/run_*/series.csv", "artifacts/baseline/summary_mc.csv"]
  repo_paths_hint: ["s120_inequality_innovation/mc/runner.py", "s120_inequality_innovation/io/writer.py"]
  estimate: M

- id: T-SFCTOOLS-INTEGRATE
  title: Integrate real sfctools; residual checks & diagnostics
  rationale: Use tested SFC engine; fail fast on accounting errors.
  paper_refs:
    - {section: "Stock–flow consistency", page: null, eq_or_fig_or_tab: "FlowMatrix guidance"}
  deps: ["T-SCHED"]
  instructions: Use PyPI sfctools; add fm_residuals.csv (max row/col abs) at cut-points; strict mode toggle.
  acceptance_criteria: "5-period smoke: residuals ≤1e-10 at all cut-points; tests pass locally."
  artifacts_expected: ["artifacts/smoke/fm_residuals.csv", "tests/test_flowmatrix_consistency.py"]
  repo_paths_hint: ["requirements.txt", "s120_inequality_innovation/core/flowmatrix_glue.py"]
  estimate: S

- id: T-ORACLE-HARNESS
  title: JPype primary harness; Py4J fallback
  rationale: Programmatic launches of JMAB+S120 model as oracle.
  paper_refs:
    - {section: "JMAB entry point & config", page: null, eq_or_fig_or_tab: "SimulationManager; jabm.config"}
  deps: ["T-MC"]
  instructions: startJVM(classpath=[...]); System.setProperty("jabm.config", xml); SimulationManager.main([]) with Desktop fallback.
  acceptance_criteria: "CLI help works; dry-run prints resolved cp/xml; baseline run produces CSVs (locally)."
  artifacts_expected: ["s120_inequality_innovation/oracle/*.py", "oracle/README.md"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/"]
  estimate: M

- id: T-ORACLE-CSV-EXPORT
  title: Standardize Java→CSV output schema
  rationale: Ensure reproducible, parsable outputs (canonical headers).
  paper_refs:
    - {section: "Variables & metrics", page: null, eq_or_fig_or_tab: "Figures/Tables variable set"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Collector outputs: t,GDP,CONS,INV,INFL,UNEMP,PROD_C,Gini_income,Gini_wealth,Debt_GDP. Canonicalize headers & paths.
  acceptance_criteria: "Canonical series.csv; meta.json includes params, seed, raw_sources, java_run_ok/java_error."
  artifacts_expected: ["artifacts/golden_java/<run>/series.csv", "artifacts/golden_java/<run>/meta.json"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/", "artifacts/golden_java/"]
  estimate: M

- id: T-ORACLE-WSL-SETUP
  title: WSL Java setup & classpath wiring (JMAB + S120)
  rationale: Enable headless CLI/JPype launches locally.
  paper_refs:
    - {section: "JMAB overview", page: null, eq_or_fig_or_tab: "Main class & system property"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Install OpenJDK; clone jmab and InequalityInnovation; compile; construct CLASSPATH and XML path.
  acceptance_criteria: "java -version ≥ 17; SimulationManager runs with -Djabm.config=<xml> in a local smoke run; classpath recorded."
  artifacts_expected: ["docs/java_wsl_setup.md", "s120_inequality_innovation/oracle/classpath.txt"]
  repo_paths_hint: ["docs/", "s120_inequality_innovation/oracle/"]
  estimate: S

- id: T-ORACLE-RUN-FRONTIERS
  title: Oracle runs – Baseline + frontier scenarios (local, no placeholders)
  rationale: Golden CSVs for acceptance tests.
  paper_refs:
    - {section: "Policy levers", page: null, eq_or_fig_or_tab: "θ (progressive tax), tu (wage rigidity)"}
  deps: ["T-ORACLE-CSV-EXPORT", "T-ORACLE-WSL-SETUP", "T-ORACLE-SEED", "T-META-STATUS"]
  instructions: Run baseline; θ∈{0.0,1.5}; tu∈{1,4}; fixed seed/horizon; scenario-specific `fileNamePrefix`; canonicalize outputs (locally).
  acceptance_criteria: "5 runs present; canonical headers; meta.json includes seed & θ/tu; `raw_sources` has no 'FALLBACK:'; `java_run_ok=true`; scenario series differ from baseline in ≥3 of {GDP,CONS,INV,INFL,UNEMP,PROD_C}."
  artifacts_expected:
    ["artifacts/golden_java/baseline/series.csv",
     "artifacts/golden_java/tax_theta0.0/series.csv",
     "artifacts/golden_java/tax_theta1.5/series.csv",
     "artifacts/golden_java/wage_tu1/series.csv",
     "artifacts/golden_java/wage_tu4/series.csv"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/cli.py", "artifacts/golden_java/*"]
  estimate: M

- id: T-ORACLE-SEED
  title: Deterministic seeding for Java oracle + provenance
  rationale: Reproducibility across baseline/frontiers.
  paper_refs:
    - {section: "Simulation setup", page: null, eq_or_fig_or_tab: "seed & horizon"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Pass a seed via Java System properties; stamp into meta.json; add a 10-period reproducibility smoke check (local).
  acceptance_criteria: "Seed in meta is an integer; re-running a 10‑period baseline with the same seed reproduces identical GDP for t=1..10; small text log saved."
  artifacts_expected: ["artifacts/golden_java/repro_check.txt"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/*", "artifacts/golden_java/"]
  estimate: S

- id: T-META-STATUS
  title: Meta run-status stamping in collector
  rationale: Avoids silent failures when Java run falls back to collection.
  paper_refs:
    - {section: "Diagnostics", page: null, eq_or_fig_or_tab: "Run metadata"}
  deps: ["T-ORACLE-CSV-EXPORT"]
  instructions: In collector: set `java_run_ok` and `java_error` based on JPype call outcome; default consistently if not executed.
  acceptance_criteria: "meta.json contains run-status fields for every scenario."
  artifacts_expected: ["artifacts/golden_java/<run>/meta.json"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/cli.py"]
  estimate: XS

- id: T-PARAM-HARMONIZE
  title: Harmonize YAML with Java XML (one-to-one map)
  rationale: Prevent calibration drift in Python vs Java.
  paper_refs:
    - {section: "Appendix A Table 1", page: null, eq_or_fig_or_tab: "Param registry"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Extract XML params; map to YAML via param_map.yaml; produce diff & doc.
  acceptance_criteria: "params_extracted.json exists; reports/params_mapping.md diff empty or justified."
  artifacts_expected: ["artifacts/golden_java/params_extracted.json", "reports/params_mapping.md"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/extract_params.py", "s120_inequality_innovation/config/param_map.yaml"]
  estimate: M

- id: T-GOLDEN-BASELINE
  title: Python↔Java baseline acceptance test
  rationale: Automate parity checks on steady window.
  paper_refs:
    - {section: "Validation window", page: null, eq_or_fig_or_tab: "t=501–1000"}
  deps: ["T-ORACLE-RUN-FRONTIERS", "T-SFCTOOLS-INTEGRATE"]
  instructions: Align series; compute window means; assert relative error ≤10% for GDP, C, I, INFL, UNEMP, PROD_C.
  acceptance_criteria: "tests/test_parity_baseline.py passes locally; reports/baseline_parity.md written with non‑trivial errors (not all 0.0%) and all ≤10%."
  artifacts_expected: ["reports/baseline_parity.md", "tests/test_parity_baseline.py"]
  repo_paths_hint: ["s120_inequality_innovation/io/golden_compare.py", "tests/*"]
  estimate: M

- id: T-GOLDEN-EXPTS
  title: Acceptance tests for θ- and tu-sweeps
  rationale: Lock experiment outcomes & guard regressions.
  paper_refs:
    - {section: "Policy experiments", page: null, eq_or_fig_or_tab: "Deltas vs baseline"}
  deps: ["T-GOLDEN-BASELINE"]
  instructions: Compute (MC window mean) deltas vs baseline; assert sign & ordering; |Δ| error ≤10%.
  acceptance_criteria: "tests/test_parity_experiments.py passes; reports/experiments_parity.md"
  artifacts_expected: ["reports/experiments_parity.md", "tests/test_parity_experiments.py"]
  repo_paths_hint: ["s120_inequality_innovation/mc/runner.py", "s120_inequality_innovation/io/golden_compare.py"]
  estimate: M
```

8. SNAPSHOT

- CI removed; local guard script in place. Oracle harness unchanged this round. Ready to run seeded goldens locally when classpath/XML are provided.

9. GIT COMMITS MADE

- chore(repo): remove CI and badges; add local golden_guard.py

10. NEXT SUGGESTED STEPS

- Set `S120_ORACLE_CLASSPATH` and update the headless XML import path to your local `ModelInnovationDistribution3.xml`.
- Run the 5 seeded scenarios to generate real goldens; confirm `java_run_ok=true` and no `FALLBACK:`.
- Run `python scripts/golden_guard.py` and the repro smoke; then recompute `reports/baseline_parity.md` with the real baseline.
- Expand `config/param_map.yaml` and regenerate `reports/params_mapping.md` to cover required parameters.

