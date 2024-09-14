import sys
from typing import List, Dict, Optional, Tuple, Set
import heapq
import time

class Literal:
    def __init__(self, variable: int, is_positive: bool):
        self.variable = abs(variable)
        self.is_positive = is_positive

    def __neg__(self):
        return Literal(self.variable, not self.is_positive)

    def __eq__(self, other):
        return self.variable == other.variable and self.is_positive == other.is_positive

    def __hash__(self):
        return hash((self.variable, self.is_positive))

    def __str__(self):
        return str(self.variable) if self.is_positive else f"-{self.variable}"

class Clause:
    def __init__(self, literals: List[Literal]):
        self.literals = frozenset(literals)
        self.watched = []

    def __str__(self):
        return ' ∨ '.join(str(lit) for lit in sorted(self.literals, key=lambda l: l.variable))

class Formula:
    def __init__(self, clauses: List[Clause]):
        self.clauses = clauses
        self.variable_to_clauses = {}
        self.watches = {}
        for i, clause in enumerate(clauses):
            for literal in clause.literals:
                if literal.variable not in self.variable_to_clauses:
                    self.variable_to_clauses[literal.variable] = set()
                self.variable_to_clauses[literal.variable].add(i)
                
                if literal not in self.watches:
                    self.watches[literal] = set()
                
                if len(clause.watched) < 2:
                    self.watches[literal].add(i)
                    clause.watched.append(literal)

    def __str__(self):
        return ' ∧ '.join(f'({clause})' for clause in self.clauses)

def parse_dimacs_file(file_path: str) -> Formula:
    clauses = []
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith('c') or line.startswith('p'):
                continue
            literals = [Literal(int(x), int(x) > 0) for x in line.split()[:-1]]
            clauses.append(Clause(literals))
    return Formula(clauses)

class CDCLSolver:
    def __init__(self, formula: Formula):
        self.formula = formula
        self.assignment = {}
        self.decision_level = {var: 0 for var in formula.variable_to_clauses.keys()}
        self.implication_graph = {}
        self.level = 0
        self.variable_order = list(formula.variable_to_clauses.keys())
        self.restart_limit = 100
        self.restart_count = 0

    def update_vsids_scores(self, clause):
        for literal in clause:
            self.vsids_scores[literal.variable] += self.vsids_bump_amount
            for i, (score, var) in enumerate(self.vsids_heap):
                if var == literal.variable:
                    self.vsids_heap[i] = (self.vsids_scores[literal.variable], var)
                    break
        heapq.heapify(self.vsids_heap)
        
        # vsids decay
        for var in self.vsids_scores:
            self.vsids_scores[var] *= self.vsids_decay_factor

        self.vsids_bump_amount /= self.vsids_decay_factor

    def get_next_decision_variable(self):
        while self.vsids_heap:
            _, var = heapq.heappop(self.vsids_heap)
            if var not in self.assignment:
                return var
        return None

    def initialize_jw_scores(self, clauses):
        self.jw_scores.clear()
        for clause in clauses:
            weight = 2 ** -len(clause)
            for literal in clause:
                self.jw_scores[abs(literal)] += weight

    def update_jw_scores(self, learned_clause):
        weight = 2 ** -len(learned_clause)
        for literal in learned_clause:
            self.jw_scores[abs(literal)] += weight

    def get_next_decision_variable_jw(self):
        unassigned_vars = [var for var in self.jw_scores if var not in self.assignment]
        if not unassigned_vars:
            return None
        return max(unassigned_vars, key=lambda var: self.jw_scores[var])

    def unit_propagation(self) -> Optional[Clause]:
        propagation_queue = [(var, val) for var, val in self.assignment.items()]
        while propagation_queue:
            variable, value = propagation_queue.pop(0)
            print(f"Propagating: {variable} = {value}")
            
            literal = Literal(variable, not value)
            for clause_index in self.formula.watches.get(literal, set()).copy():
                clause = self.formula.clauses[clause_index]
                
                other_watch = next(lit for lit in clause.watched if lit != literal)
                
                # clause alrdy satisfied
                if other_watch.variable in self.assignment and self.assignment[other_watch.variable] == other_watch.is_positive:
                    continue  
                
                new_watch = None
                for lit in clause.literals:
                    if lit not in clause.watched and (lit.variable not in self.assignment or self.assignment[lit.variable] == lit.is_positive):
                        new_watch = lit
                        break
                
                if new_watch:
                    clause.watched.remove(literal)
                    clause.watched.append(new_watch)
                    self.formula.watches[literal].remove(clause_index)
                    if new_watch not in self.formula.watches:
                        self.formula.watches[new_watch] = set()
                    self.formula.watches[new_watch].add(clause_index)
                else:
                    if other_watch.variable not in self.assignment:
                        self.assignment[other_watch.variable] = other_watch.is_positive
                        self.decision_level[other_watch.variable] = self.level
                        self.implication_graph[other_watch.variable] = clause
                        propagation_queue.append((other_watch.variable, other_watch.is_positive))
                        print(f"Unit propagation: {other_watch.variable} = {other_watch.is_positive}")
                    elif self.assignment[other_watch.variable] != other_watch.is_positive:
                        print(f"Conflict found: {clause}")
                        return clause
        
        return None

    def backtrack(self, level: int):
        for var, assigned_level in list(self.decision_level.items()):
            if assigned_level > level:
                del self.assignment[var]
                del self.decision_level[var]
                if var in self.implication_graph:
                    del self.implication_graph[var]
        self.level = level

    def analyze_conflict(self, conflict_clause: Clause) -> Tuple[Clause, int]:
        learned_clause = set(conflict_clause.literals)
        current_level_literals = set()
        seen = set()
        
        while True:
            for literal in learned_clause:
                if literal.variable not in seen:
                    seen.add(literal.variable)
                    level = self.decision_level.get(literal.variable, 0)
                    if level == self.level:
                        current_level_literals.add(literal)
                    elif level > 0:
                        learned_clause.add(-Literal(literal.variable, not literal.is_positive))
            
            if len(current_level_literals) <= 1:
                break
            
            literal = current_level_literals.pop()
            learned_clause.remove(literal)
            if literal.variable in self.implication_graph:
                antecedent = self.implication_graph[literal.variable]
                learned_clause.update(antecedent.literals)
        
        backtrack_level = 0
        for literal in learned_clause:
            level = self.decision_level.get(literal.variable, 0)
            if level != self.level and level > backtrack_level:
                backtrack_level = level
        
        return Clause(list(learned_clause)), backtrack_level
    
    def solve(self) -> Optional[Dict[int, bool]]:
        while True:
            self.restart_count += 1
            if self.restart_count > self.restart_limit:
                self.restart_count = 0
                self.backtrack(0)
                print("Restarting solver")
            conflict = self.unit_propagation()
            print(f"Level: {self.level}, Assignment: {self.assignment}")
            print(f"Conflict: {conflict}")
            
            if conflict is None:
                if len(self.assignment) == len(self.variable_order):
                    return self.assignment
                
                self.level += 1
                for var in self.variable_order:
                    if var not in self.assignment:
                        self.assignment[var] = True
                        self.decision_level[var] = self.level
                        print(f"Decision: Assigning {var} = True at level {self.level}")
                        break
            else:
                if self.level == 0:
                    return None
                
                learned_clause, backtrack_level = self.analyze_conflict(conflict)
                print(f"Learned clause: {learned_clause}, Backtrack level: {backtrack_level}")
                self.formula.clauses.append(learned_clause)
                
                # initialize watched literals
                learned_clause.watched = []
                for literal in learned_clause.literals:
                    if literal.variable not in self.formula.variable_to_clauses:
                        self.formula.variable_to_clauses[literal.variable] = set()
                    self.formula.variable_to_clauses[literal.variable].add(len(self.formula.clauses) - 1)
                    if literal.variable not in self.decision_level:
                        self.decision_level[literal.variable] = 0
                    
                    if len(learned_clause.watched) < 2:
                        if literal not in self.formula.watches:
                            self.formula.watches[literal] = set()
                        self.formula.watches[literal].add(len(self.formula.clauses) - 1)
                        learned_clause.watched.append(literal)
                
                self.backtrack(backtrack_level)
                print(f"Backtracked to level {backtrack_level}")
                
                # unit propafation for learned clause
                for literal in learned_clause.literals:
                    if literal.variable not in self.assignment:
                        self.assignment[literal.variable] = literal.is_positive
                        self.decision_level[literal.variable] = backtrack_level
                        self.implication_graph[literal.variable] = learned_clause
                        print(f"Unit propagation from learned clause: {literal.variable} = {literal.is_positive}")
                        break

def solve_sat(file_path: str) -> Optional[Dict[int, bool]]:
    formula = parse_dimacs_file(file_path)
    solver = CDCLSolver(formula)
    solution = solver.solve()

    if solution:
        return {var: val for var, val in solution.items()}
    return None

def main():
    dimacs_file = "test.cnf"
    
    start_time = time.time()
    
    solution = solve_sat(dimacs_file)
    
    end_time = time.time()
    solve_time = end_time - start_time 

    if solution:
        print("SAT")
        print("Solution:", " ".join(f"{k if v else -k}" for k, v in sorted(solution.items())))
    else:
        print("UNSAT")
    
    print(f"Solving time: {solve_time:.4f} seconds")

if __name__ == "__main__":
    main()