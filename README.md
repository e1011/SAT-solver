This project implements an optimized solver for the NP-Complete SAT problem in Python. The SAT problem involves determining whether there exists an assignment of variables that satisfies a given Boolean formula.

Example:  
Given the formula: (x ∨ y) ∧ (¬x ∨ z) ∧ (¬y ∨ ¬z)  
A satisfying assignment would be: x = true, y = false, z = true  
## Features

- **Watched Literals**: Two literals are watched to reduce the number of operations during propagation
- **Conflict-Driven Clause Learning (CDCL)**: Learns new clauses from conflicts to prune the search space effectively.
- **Variable Selection Heuristics**:
  - VSIDS (Variable State Independent Decaying Sum)
  - Jeroslow-Wang
- **Random Restarts**: Periodically restarts the search to escape from local minima.

## Components

### 1. SAT Solver
1. Place your CNF formula in a file named `test.cnf` in the project directory.
2. Run the solver:
   ```
   python main.py  
   ```

[CNF](https://people.sc.fsu.edu/~jburkardt/data/cnf/cnf.html) is a standard format for representing Boolean formulas.

Example:
```
p cnf 
1 2 -3 0
-1 -2 3 0
2 3 0
```
This represents the formula: (x₁ ∨ x₂ ∨ ¬x₃) ∧ (¬x₁ ∨ ¬x₂ ∨ x₃) ∧ (x₂ ∨ x)

### 2. CNF Generator

A tool to generate random SAT instances in CNF format.

#### Usage

```
python generator.py <# variables> <# clauses> <min clause length> <max clause length> <# of files>
```

Example:
```
python generator.py 100 400 3 7 5
```
This generates 5 files in the `tests` folder, each with 100 variables, 400 clauses, and clause lengths between 3 and 7.

#### Output

Generated files are placed in the `tests` folder with a comment indicating whether they are satisfiable or not (determined using MiniSat).

