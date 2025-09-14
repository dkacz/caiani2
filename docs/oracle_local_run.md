% Local Golden Generation (Java Oracle) – Seeded, Headless

This guide shows how to generate canonical Java “golden” outputs locally for the S120 Caiani AB‑SFC model using our seeded, headless harness. All verification is done locally; there is no GitHub Actions CI in this repo.

## Prerequisites
- OpenJDK 17 installed (`java -version` prints 17+)
- Python environment with this repo installed (`pip install -e .`)
- JMAB + InequalityInnovation model built locally (classes/jars)
- A Spring XML configuration for the model (e.g., `InequalityInnovation.xml`) or the provided headless XML adjusted to your machine

## Classpath and XML
You can provide these via CLI flags or environment variables:

- `S120_ORACLE_CLASSPATH`: full Java classpath including JMAB, the model classes, and required libs. Example (Linux):
  - `export S120_ORACLE_CLASSPATH="$HOME/work/jmab/bin:$HOME/work/InequalityInnovation/bin:$HOME/work/InequalityInnovation/lib/*:$HOME/work/jars/jabm-0.9.9.jar"`
- `S120_ORACLE_XML`: Spring XML config. Prefer your model’s main XML (recommended), or use the headless file included here once you adjust absolute paths.

Headless XML option provided in-repo:
- `artifacts/golden_java/headless/main_headless.xml` and `artifacts/golden_java/headless/reports_headless.xml`
- Before use, edit `main_headless.xml` to point `import resource="...ModelInnovationDistribution3.xml"` to your local absolute path where the model XML lives, and ensure the `reports_headless.xml` import points to this repo’s file on your machine.
- The Python harness will patch `fileNamePrefix` per scenario automatically to write under `artifacts/golden_java/<scenario>/data/`.

## Canonical schema
Each scenario collects to:
- `artifacts/golden_java/<scenario>/series.csv` with exact headers:
  - `t,GDP,CONS,INV,INFL,UNEMP,PROD_C,Gini_income,Gini_wealth,Debt_GDP`
- `artifacts/golden_java/<scenario>/meta.json` with `seed` (int), `horizon`, `theta`, `tu`, `raw_sources`, `fileNamePrefix`, and run-status fields `java_run_ok` (bool) and `java_error` (string or null).

## Run commands (seeded)
You may pass flags or rely on env vars. Replace `...` with your actual paths when not using env.

- Baseline:
  - `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml --seed 12345 baseline`
- Tax frontier θ=0.0 and θ=1.5:
  - `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml --seed 12345 tax --theta 0.0`
  - `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml --seed 12345 tax --theta 1.5`
- Wage frontier tu=1 and tu=4:
  - `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml --seed 12345 wage --tu 1`
  - `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml --seed 12345 wage --tu 4`

Collector (only if you need to re-collect from an existing run dir):
- `python -m s120_inequality_innovation.oracle.cli --xml artifacts/golden_java/headless/main_headless.xml collect --scenario baseline`

## Reproducibility smoke (10 periods)
- `python -m s120_inequality_innovation.oracle.cli --classpath "$S120_ORACLE_CLASSPATH" --xml artifacts/golden_java/headless/main_headless.xml repro --seed 12345`
- Check `artifacts/golden_java/repro_check.txt` — it should say `PASSED` when classpath/XML are correct and the oracle is deterministic with the given seed.

## Acceptance checks (local)
- `meta.json.raw_sources` must not contain any `FALLBACK:` entries.
- For each frontier, the window mean (t=501–1000) must differ from baseline in ≥3 of {GDP, CONS, INV, INFL, UNEMP, PROD_C}.

## Troubleshooting
- “Could not load a SimulationManager class from classpath”: your `S120_ORACLE_CLASSPATH` is incomplete or incorrect. Include both model classes and required `jabm`/deps.
- Empty or NaN `series.csv`: verify `fileNamePrefix` in the scenario XML points under the scenario `data/` directory. The harness patches this automatically, but if your base XML has conflicting beans, ensure only one `fileNamePrefix` bean is active.
- Mixed or non-canonical headers: the collector canonicalizes a broad set of known report names. If a key metric is missing, ensure the corresponding report is enabled in the model XML and re-run.
- Repro check `FAILED`: confirm the seed is making its way into the oracle. The harness sets `jabm.seed`, `JABM_SEED`, and `seed` System properties.

## Notes
- Heavy Java simulations and guards run locally. Use `scripts/golden_guard.py` after generating goldens.
- To regenerate parameters mapping: see `docs/java_wsl_setup.md` and `s120_inequality_innovation/oracle/extract_params.py`.
