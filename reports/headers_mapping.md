# Canonical Header Mapping (Java → Python)

The Java oracle (JMAB + S120/InequalityInnovation) may emit variable names that
vary slightly across builds. We normalize them to the following canonical headers
expected by our comparator and reports:

Canonical headers:
- t
- GDP
- CONS
- INV
- INFL
- UNEMP
- PROD_C
- Gini_income
- Gini_wealth
- Debt_GDP

Examples of Java→canonical renames implemented in `io/golden_compare.py`:
- RealGDP → GDP
- RealC → CONS; Consumption → CONS
- RealI → INV; Investment → INV
- Inflation or CPI_infl → INFL
- Unemployment or u → UNEMP
- ProdC or LaborProductivityC → PROD_C
- GiniIncome → Gini_income; GiniWealth → Gini_wealth
- DebtGDP → Debt_GDP

If new variants are observed, extend the mapping in `canonicalize_java_headers`.
