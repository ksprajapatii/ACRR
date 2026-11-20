# ACRR — Explainable Refactoring Report

**Functions explained:** 4

---

## process_data

- **File:** sample_app.py
- **Priority:** High
- **Score:** 76.46/100

### Why was this function prioritized?

This function received a priority score of 76.46/100 and was classified as High priority.

### Contributing factors

| Factor | Component score | Weighted contribution |
|---|---:|---:|
| smell_severity | 100 | 40.0 |
| nesting | 100.0 | 20.0 |
| complexity | 40.0 | 12.0 |
| maintainability | 44.63 | 4.46 |

### Detected code smells

- **Too Many Parameters** (Medium)
- **Deeply Nested Conditions** (High)

### Explanation

- Medium severity smell: Too Many Parameters. Function has reached or exceeded the parameter threshold.
- High severity smell: Deeply Nested Conditions. Function contains deeply nested control-flow blocks.
- Moderate cyclomatic complexity.
- Deeply nested control-flow structure.

### Recommended refactoring actions

- Consider grouping related parameters into a configuration object.
- Review whether the function has too many responsibilities.
- Use guard clauses to reduce nested conditional blocks.
- Simplify complex conditional expressions.
- Reduce cyclomatic complexity by simplifying branches and extracting helper functions.
- Reduce nesting depth using early returns and simpler control flow.
- Improve maintainability by simplifying the function structure.

---

## OrderProcessor.calculate_total

- **File:** sample_app.py
- **Priority:** High
- **Score:** 76.46/100

### Why was this function prioritized?

This function received a priority score of 76.46/100 and was classified as High priority.

### Contributing factors

| Factor | Component score | Weighted contribution |
|---|---:|---:|
| smell_severity | 100 | 40.0 |
| nesting | 100.0 | 20.0 |
| complexity | 40.0 | 12.0 |
| maintainability | 44.63 | 4.46 |

### Detected code smells

- **Deeply Nested Conditions** (High)

### Explanation

- High severity smell: Deeply Nested Conditions. Function contains deeply nested control-flow blocks.
- Moderate cyclomatic complexity.
- Deeply nested control-flow structure.

### Recommended refactoring actions

- Use guard clauses to reduce nested conditional blocks.
- Simplify complex conditional expressions.
- Reduce cyclomatic complexity by simplifying branches and extracting helper functions.
- Reduce nesting depth using early returns and simpler control flow.
- Improve maintainability by simplifying the function structure.

---

## check_access

- **File:** guard_clause_demo.py
- **Priority:** High
- **Score:** 72.0/100

### Why was this function prioritized?

This function received a priority score of 72.0/100 and was classified as High priority.

### Contributing factors

| Factor | Component score | Weighted contribution |
|---|---:|---:|
| smell_severity | 100 | 40.0 |
| nesting | 100.0 | 20.0 |
| complexity | 40.0 | 12.0 |
| maintainability | 0.0 | 0.0 |

### Detected code smells

- **Deeply Nested Conditions** (High)

### Explanation

- High severity smell: Deeply Nested Conditions. Function contains deeply nested control-flow blocks.
- Moderate cyclomatic complexity.
- Deeply nested control-flow structure.

### Recommended refactoring actions

- Use guard clauses to reduce nested conditional blocks.
- Simplify complex conditional expressions.
- Reduce cyclomatic complexity by simplifying branches and extracting helper functions.
- Reduce nesting depth using early returns and simpler control flow.

---

## classify_number

- **File:** sample_app.py
- **Priority:** Low
- **Score:** 26.79/100

### Why was this function prioritized?

This function received a priority score of 26.79/100 and was classified as Low priority.

### Contributing factors

| Factor | Component score | Weighted contribution |
|---|---:|---:|
| nesting | 66.67 | 13.33 |
| complexity | 30.0 | 9.0 |
| maintainability | 44.63 | 4.46 |
| smell_severity | 0.0 | 0.0 |

### Detected code smells

- No function-level code smells detected.

### Explanation

- Moderate nesting depth.

### Recommended refactoring actions

- Reduce nesting depth using early returns and simpler control flow.
- Improve maintainability by simplifying the function structure.
