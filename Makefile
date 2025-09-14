PY=python3

.PHONY: smoke oracle-baseline oracle-frontiers parity figures slice1 slice2 slice3 oracle-setup-dryrun

smoke:
	$(PY) -c "from s120_inequality_innovation.mc.runner import run_baseline_smoke; run_baseline_smoke()"
	$(PY) -c "from s120_inequality_innovation.io.plots import plot_smoke; plot_smoke()"

oracle-baseline:
	$(PY) -m s120_inequality_innovation.oracle.cli baseline \
		--classpath "$$S120_ORACLE_CLASSPATH" \
		--xml "$$S120_ORACLE_XML" \
		--outroot artifacts/golden_java || true

oracle-frontiers:
	$(PY) -m s120_inequality_innovation.oracle.cli tax --theta 0.0 \
		--classpath "$$S120_ORACLE_CLASSPATH" --xml "$$S120_ORACLE_XML" --outroot artifacts/golden_java || true
	$(PY) -m s120_inequality_innovation.oracle.cli tax --theta 1.5 \
		--classpath "$$S120_ORACLE_CLASSPATH" --xml "$$S120_ORACLE_XML" --outroot artifacts/golden_java || true
	$(PY) -m s120_inequality_innovation.oracle.cli wage --tu 1 \
		--classpath "$$S120_ORACLE_CLASSPATH" --xml "$$S120_ORACLE_XML" --outroot artifacts/golden_java || true
	$(PY) -m s120_inequality_innovation.oracle.cli wage --tu 4 \
		--classpath "$$S120_ORACLE_CLASSPATH" --xml "$$S120_ORACLE_XML" --outroot artifacts/golden_java || true

parity:
	pytest -q -k parity || true

figures:
	$(PY) -c "from s120_inequality_innovation.io.plots import plot_smoke; plot_smoke()"

.PHONY: param-map
param-map:
	$(PY) -m s120_inequality_innovation.oracle.extract_params --xml "$$S120_ORACLE_XML" --out artifacts/golden_java/params_extracted.json --map s120_inequality_innovation/config/param_map.yaml --report

.PHONY: parity-report
parity-report:
	$(PY) - <<'PY'
from pathlib import Path
from s120_inequality_innovation.io.golden_compare import compare_baseline, write_baseline_report
pr = Path('artifacts/baseline/run_001/series.csv')
jr = Path('artifacts/golden_java/baseline/series.csv')
res = compare_baseline(pr, jr)
write_baseline_report(res, Path('reports/baseline_parity.md'))
print(res.rel_errors)
PY

.PHONY: slice1
slice1:
	$(PY) -m s120_inequality_innovation.mc.slice1_runner

slice2:
	$(PY) -m s120_inequality_innovation.mc.slice2_runner

slice3:
	$(PY) -m s120_inequality_innovation.mc.slice3_runner

oracle-setup-dryrun:
	$(PY) -m s120_inequality_innovation.oracle.jpype_harness --dry-run \
		--classpath "$$S120_ORACLE_CLASSPATH" --xml "$$S120_ORACLE_XML"
