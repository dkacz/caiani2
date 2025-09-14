% Updated Backlog

```yaml
- id: M1
  title: Milestone – Engine ready (sfctools skeleton, scheduler, MC, CI)
  rationale: Deterministic SFC engine with the 19-step loop, artifacting, diagnostics, and CI.
  paper_refs:
    - {section: "Sequencing & accounting discipline", page: null, eq_or_fig_or_tab: "19-step; FlowMatrix"}
  deps: []
  instructions: FlowMatrix glue; 19-step scheduler; seeds & MC runner; CI.
  acceptance_criteria: "FlowMatrix checks pass at steps 3/7/12/16/19; smoke MC creates non-empty CSVs; CI green."
  artifacts_expected: ["artifacts/smoke/.csv", ".github/workflows/ci.yml"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: M2
  title: Milestone – Baseline parity vs Java
  rationale: Match baseline macro & inequality dynamics to oracle within tolerances.
  paper_refs:
    - {section: "Baseline & validation window", page: null, eq_or_fig_or_tab: "t=501–1000; macro panels"}
  deps: ["M1", "T-ORACLE-RUN-FRONTIERS", "T-GOLDEN-BASELINE", "T-BL-SLICE1", "T-BL-SLICE2", "T-BL-SLICE3-EXT"]
  instructions: Implement baseline behaviors and compare to Java golden CSVs (baseline).
  acceptance_criteria: "MC means (t=501–1000) for GDP, C, I, inflation, unemployment, C‑sector productivity within ±10% of oracle; co-movements preserved; inequality paths qualitatively consistent."
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
  acceptance_criteria: "params_default.yaml keys/values match Table 1; tests pass."
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
  acceptance_criteria: "Unit test enumerates 19 labels; SFC check passes in smoke."
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
  acceptance_criteria: "25-run baseline executes; seeds logged; summary exists."
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
  acceptance_criteria: "5-period smoke: residuals ≤1e-10 at all cut-points; tests pass."
  artifacts_expected: ["artifacts/smoke/fm_residuals.csv", "tests/test_flowmatrix_consistency.py"]
  repo_paths_hint: ["requirements.txt", "s120_inequality_innovation/core/flowmatrix_glue.py"]
  estimate: S

- id: T-ORACLE-HARNESS
  title: JPype primary harness; Py4J fallback
  rationale: Programmatic launches of JMAB+S120 model as oracle.
  paper_refs:
    - {section: "JMAB entry point & config", page: null, eq_or_fig_or_tab: "DesktopSimulationManager; jabm.config"}
  deps: ["T-MC"]
  instructions: startJVM(classpath=[...]); System.setProperty("jabm.config", xml); SimulationManager.main([]) with Desktop fallback.
  acceptance_criteria: "CLI help works; dry-run prints resolved cp/xml; baseline run produces CSVs."
  artifacts_expected: ["s120_inequality_innovation/oracle/*.py", "oracle/README.md"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/"]
  estimate: M

- id: T-ORACLE-CSV-EXPORT
  title: Standardize Java→CSV output schema
  rationale: Ensure reproducible, parsable outputs (canonical headers).
  paper_refs:
    - {section: "Variables & metrics", page: null, eq_or_fig_or_tab: "Figures/Tables variable set"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Configure observers or collector to output: t,GDP,CONS,INV,INFL,UNEMP,PROD_C,Gini_income,Gini_wealth,Debt_GDP. Canonicalize headers & paths.
  acceptance_criteria: "Canonical `series.csv` with exact headers; `meta.json` includes params & seed."
  artifacts_expected: ["artifacts/golden_java/<run>/series.csv", "artifacts/golden_java/<run>/meta.json"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/", "artifacts/golden_java/"]
  estimate: M

- id: T-ORACLE-WSL-SETUP
  title: WSL Java setup & classpath wiring (JMAB + S120)
  rationale: Enable headless CLI/JPype launches in WSL.
  paper_refs:
    - {section: "JMAB overview", page: null, eq_or_fig_or_tab: "Main class & system property"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Install OpenJDK; clone jmab and InequalityInnovation; compile; construct CLASSPATH and XML path.
  acceptance_criteria: "java -version ≥ 17; SimulationManager runs with -Djabm.config=<xml> in a smoke run; classpath file recorded."
  artifacts_expected: ["docs/java_wsl_setup.md", "s120_inequality_innovation/oracle/classpath.txt"]
  repo_paths_hint: ["docs/", "s120_inequality_innovation/oracle/"]
  estimate: S

- id: T-ORACLE-RUN-FRONTIERS
  title: Oracle runs – Baseline + frontier scenarios (no placeholders)
  rationale: Golden CSVs for acceptance tests.
  paper_refs:
    - {section: "Policy levers", page: null, eq_or_fig_or_tab: "θ (progressive tax), tu (wage rigidity)"}
  deps: ["T-ORACLE-CSV-EXPORT", "T-ORACLE-WSL-SETUP", "T-ORACLE-SEED", "T-META-STATUS"]
  instructions: Run baseline; θ∈{0.0,1.5}; tu∈{1,4}; fixed seed/horizon; ensure scenario-specific `fileNamePrefix`; canonicalize outputs.
  acceptance_criteria: "5 runs present; canonical headers; meta.json includes seed & effective θ/tu; `meta.raw_sources` contains no 'FALLBACK:'; scenario `series.csv` differ from baseline in ≥3 of {GDP,CONS,INV,INFL,UNEMP,PROD_C}."
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
  rationale: Reproducibility across baseline/frontiers and CI.
  paper_refs:
    - {section: "Simulation setup", page: null, eq_or_fig_or_tab: "seed & horizon"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Pass a seed into JABM/SimulationManager (env or system property); log it; stamp into `meta.json`; add a 10-period reproducibility smoke check.
  acceptance_criteria: "Seed in meta is an integer; re-running a 10‑period baseline with the same seed reproduces identical GDP for t=1..10; small text log saved."
  artifacts_expected: ["artifacts/golden_java/repro_check.txt"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/*", "ci/"]
  estimate: S

- id: T-META-STATUS
  title: Meta run-status stamping in collector
  rationale: Avoids silent failures when Java run falls back to collection.
  paper_refs:
    - {section: "Diagnostics", page: null, eq_or_fig_or_tab: "Run metadata"}
  deps: ["T-ORACLE-CSV-EXPORT"]
  instructions: In collector: set `java_run_ok: true/false` and `java_error` (string) in meta.json depending on JPype call outcome.
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
  instructions: Align series; compute window means; assert relative error ≤10% for GDP, C, I, inflation, unemployment, productivity.
  acceptance_criteria: "tests/test_parity_baseline.py passes; reports/baseline_parity.md written with non‑trivial errors (not all 0.0%) and all ≤10%."
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

- id: T-BL-SLICE1
  title: Baseline behaviour slice 1 (Eqs. 3.1–3.10, 3.22)
  rationale: Expectations, output/inventories, labor demand, pricing/markup, wage revision.
  paper_refs:
    - {section: "Model core", page: null, eq_or_fig_or_tab: "Eqs. 3.1–3.2, 3.3–3.6, 3.9–3.10, 3.22"}
  deps: ["T-SFCTOOLS-INTEGRATE"]
  instructions: Implement and wire steps 1–3, 9, 12, 14 with FlowMatrix entries.
  acceptance_criteria: "100-period run closes SFC; inventory ratio near ν±0.05 by t≥50; wages>0; μ∈[0,1]."
  artifacts_expected: ["artifacts/python/baseline_slice1/run_*/series.csv", "artifacts/python/baseline_slice1/fm_residuals.csv"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice1_engine.py", "s120_inequality_innovation/mc/slice1_runner.py"]
  estimate: M

- id: T-BL-SLICE2
  title: Baseline behaviour slice 2 – Investment, capital vintages, innovation/imitation (Eqs. 3.11–3.16; Steps 4–5–10–11)
  rationale: Add capital accumulation & Schumpeterian dynamics driving productivity/growth.
  paper_refs:
    - {section: "Investment & innovation", page: null, eq_or_fig_or_tab: "Eqs. 3.11–3.16"}
  deps: ["T-BL-SLICE1"]
  instructions: Desired capacity growth; investment demand; vintage comparison (ε intensity); R&D success & imitation probabilities; t+1 delivery.
  acceptance_criteria: "300‑period run: PROD_C trend >0; Step‑11 lag respected; SFC residuals ≤1e‑10; innovation success rates within ±10% of target over t=100–300."
  artifacts_expected: ["artifacts/python/baseline_slice2/run_001/series.csv", "artifacts/python/baseline_slice2/run_001/fm_residuals.csv", "artifacts/python/baseline_slice2/run_001/diag_innovation.csv", "reports/slice2_notes.md"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice2_engine.py", "s120_inequality_innovation/mc/slice2_runner.py"]
  estimate: L

- id: T-BL-SLICE3-EXT
  title: Baseline behaviour slice 3 – extend credit/deposits/taxes/CB/bonds to constraints & defaults
  rationale: Close financial circuit under constraints and prepare policy levers for experiments.
  paper_refs:
    - {section: "Finance & policy blocks", page: null, eq_or_fig_or_tab: "Steps 6–7–13–15–16–17–18–19; Eqs. 3.24–3.28"}
  deps: ["T-BL-SLICE2"]
  instructions: Implement bank capital & liquidity ratio constraints; deposit switching (ε, χ); CB advances & bond ops; default & recap hooks; ensure government funding identity each period.
  acceptance_criteria: "End-of-period stocks reconcile; gov deficit = Δbonds + CB ops − Δdeposits; bank constraints satisfied; SFC residuals ≤1e‑10; defaults logged."
  artifacts_expected: ["artifacts/python/baseline_slice3/run_001/series.csv", "artifacts/python/baseline_slice3/run_001/fm_residuals.csv", "artifacts/python/baseline_slice3/run_001/notes_gov_identity.csv", "reports/slice3_notes.md"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice3_engine.py", "s120_inequality_innovation/mc/slice3_runner.py"]
  estimate: L

- id: T-INEQ-METRICS
  title: Inequality metrics & figures
  rationale: Required for validation targets and experiment analysis.
  paper_refs:
    - {section: "Distributional outcomes", page: null, eq_or_fig_or_tab: "Lorenz & Gini (income/wealth)"}
  deps: ["T-BL-SLICE3-EXT"]
  instructions: Compute Lorenz curves & Gini for income and wealth per period; save MC window means; plotting scripts.
  acceptance_criteria: "CSV with per-period Gini_income & Gini_wealth; figures regenerate deterministically; comparator picks metrics when present."
  artifacts_expected: ["artifacts/python/baseline/inequality.csv", "artifacts/figures/inequality_.png"]
  repo_paths_hint: ["s120_inequality_innovation/io/plots.py", "notebooks/figures.ipynb"]
  estimate: M

- id: T-CI-SMOKE
  title: CI smoke – short-run SFC & anti-placeholder guards
  rationale: Keep CI fast while guarding basics and preventing stubbed goldens.
  paper_refs:
    - {section: "Continuous integration", page: null, eq_or_fig_or_tab: "Smoke checks"}
  deps: ["M1"]
  instructions: GitHub Actions: run 5–10 period smoke; assert SFC residuals ≤1e-10; ensure oracle CLI `--help` works (no long runs); add guards against placeholder goldens.
  acceptance_criteria: "CI job green in <10 min; artifacts uploaded for smoke; baseline meta.raw_sources has no 'FALLBACK:'; at least one frontier differs from baseline in GDP mean (when goldens are present)."
  artifacts_expected: [".github/workflows/ci.yml", "ci/smoke_log.txt"]
  repo_paths_hint: [".github/workflows/", "ci/"]
  estimate: S
```
