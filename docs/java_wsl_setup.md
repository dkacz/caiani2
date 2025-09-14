# WSL Java Setup for S120 Oracle (JMAB + InequalityInnovation)

This guide captures a minimal, reproducible setup on WSL Ubuntu to run the
S120 Java oracle via our JPype harness.

## 1) Install OpenJDK 17 and Git

```bash
sudo apt-get update && sudo apt-get install -y openjdk-17-jdk git
java -version
```

## 2) Clone the repositories under `~/work`

```bash
mkdir -p ~/work && cd ~/work
git clone https://github.com/S120/jmab.git
git clone https://github.com/S120/InequalityInnovation.git
```

## 3) Compile to `bin/` (javac example)

```bash
cd ~/work/jmab
mkdir -p bin
find src -name "*.java" > sources.txt
javac -d bin @sources.txt

cd ~/work/InequalityInnovation
mkdir -p bin
find src -name "*.java" > sources.txt
# Include jmab/bin and any jars in InequalityInnovation/lib on the classpath
javac -cp "lib/*:../jmab/bin" -d bin @sources.txt
```

## 4) Record classpath and XML

```bash
echo "$HOME/work/jmab/bin:$HOME/work/InequalityInnovation/bin:$HOME/work/InequalityInnovation/lib/*" \
  > s120_inequality_innovation/oracle/classpath.txt
export S120_ORACLE_CLASSPATH="$(cat s120_inequality_innovation/oracle/classpath.txt)"
export S120_ORACLE_XML="$HOME/work/InequalityInnovation/resources/InequalityInnovation.xml"
```

## 5) Dry-run the JPype harness

```bash
python -m s120_inequality_innovation.oracle.jpype_harness \
  --dry-run --classpath "$S120_ORACLE_CLASSPATH" --xml "$S120_ORACLE_XML"
```

## 6) Generate golden CSVs (baseline + frontiers)

```bash
make oracle-baseline
make oracle-frontiers
```

Artifacts are written under `artifacts/golden_java/...` with `series.csv` and
`meta.json` per scenario. There is no CI; run local guards with:

```bash
python scripts/golden_guard.py
```
