# Java Oracle Harness (JMAB / InequalityInnovation)

This folder contains a JPype-based harness to launch the Java oracle model
`S120/InequalityInnovation` and export golden CSVs for parity checks.

Quickstart (WSL Ubuntu):

1. Install Java 17

   sudo apt update && sudo apt install -y openjdk-17-jdk-headless git
   java -version

2. Clone the repo

   git clone https://github.com/S120/InequalityInnovation.git

3. Build or set classpath containing compiled classes and dependencies.
   Identify the Spring XML config (e.g., `resources/InequalityInnovation.xml`).

4. Launch via JPype (CLI)

   python -m s120_inequality_innovation.oracle.jpype_harness --help
   # or scenario CLI
   python -m s120_inequality_innovation.oracle.cli baseline \
       --classpath "~/work/build/java_classes:~/work/InequalityInnovation/lib/*:~/work/jmab/lib/*" \
       --xml "~/work/InequalityInnovation/resources/InequalityInnovation.xml"

The first successful run should produce CSVs in the Java side. Then copy them
under `artifacts/golden_java/<scenario>/` for use by parity tests.

Notes:
- If the repo provides an executable JAR, you can also run it via `subprocess`.
- For detailed options, refer to the repository README of `InequalityInnovation`.

FAQ – JPype convertStrings

- We call `jpype.startJVM(..., convertStrings=False)`. JPype’s quickstart suggests avoiding automatic string conversion to reduce surprises when interacting with Java APIs (e.g., method overload resolution and immutability semantics). Python strings will be wrapped as `java.lang.String` when passed; receiving Java strings behaves predictably without implicit Python conversion.

WSL + JDK Quick Steps:

1) PowerShell (Admin): wsl --install
2) Ubuntu: sudo apt update && sudo apt install -y openjdk-17-jdk-headless git
3) Verify: java -version; javac -version
4) Clone repos: git clone https://github.com/S120/jmab.git && git clone https://github.com/S120/InequalityInnovation.git
5) Compile classes (example):

   mkdir -p ~/work/build/java_classes
   find ~/work/jmab/src -name "*.java" > /tmp/jmab_sources.txt
   javac -cp "~/work/jmab/lib/*" -d ~/work/build/java_classes @/tmp/jmab_sources.txt

   find ~/work/InequalityInnovation/src -name "*.java" > /tmp/ineq_sources.txt
   javac -cp "~/work/build/java_classes:~/work/InequalityInnovation/lib/*:~/work/jmab/lib/*" \
         -d ~/work/build/java_classes @/tmp/ineq_sources.txt

6) Run via CLI (JPype): see example above.
