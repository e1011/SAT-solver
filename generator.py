import os
import random
import argparse
import subprocess
import tempfile

def ensure_tests_folder():
    if not os.path.exists('tests'):
        os.makedirs('tests')

def generate_sat_instance(num_variables, num_clauses, min_clause_length, max_clause_length, filename):
    clauses = []
    for _ in range(num_clauses):
        clause_length = random.randint(min_clause_length, max_clause_length)
        clause = []
        variables = random.sample(range(1, num_variables + 1), clause_length)
        for var in variables:
            clause.append(var if random.random() < 0.5 else -var)
        clauses.append(clause)

    filepath = os.path.join('tests', filename)
    
    # minisat input
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write(f"p cnf {num_variables} {num_clauses}\n")
        for clause in clauses:
            temp_file.write(' '.join(map(str, clause)) + ' 0\n')
        temp_filename = temp_file.name

    # minisat output
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as output_file:
        output_filename = output_file.name

    try:
        result = subprocess.run(['minisat', temp_filename, output_filename], capture_output=True, text=True)
        with open(output_filename, 'r') as f:
            minisat_output = f.read()
        is_satisfiable = "UNSAT" not in minisat_output
        solution = None
        if is_satisfiable:
            solution = minisat_output.split('\n')[1].strip()
    except FileNotFoundError:
        print("Error: minisat not found. Please install minisat and ensure it's in your PATH.")
        return
    finally:
        os.unlink(temp_filename)
        os.unlink(output_filename)

    # write the file
    with open(filepath, 'w') as f:
        f.write(f"c {'SATISFIABLE' if is_satisfiable else 'UNSATISFIABLE'}\n")
        if is_satisfiable and solution:
            f.write(f"c Solution: {solution}\n")
        f.write(f"p cnf {num_variables} {num_clauses}\n")
        for clause in clauses:
            f.write(' '.join(map(str, clause)) + ' 0\n')

def main():
    parser = argparse.ArgumentParser(description="Generate random SAT instances")
    parser.add_argument("num_variables", type=int, help="Number of variables")
    parser.add_argument("num_clauses", type=int, help="Number of clauses")
    parser.add_argument("min_clause_length", type=int, help="Minimum length of each clause")
    parser.add_argument("max_clause_length", type=int, help="Maximum length of each clause")
    parser.add_argument("num_files", type=int, help="Number of files to generate")

    args = parser.parse_args()

    ensure_tests_folder()

    for i in range(1, args.num_files + 1):
        filename = f"test{i}.cnf"
        generate_sat_instance(args.num_variables, args.num_clauses, args.min_clause_length, args.max_clause_length, filename)
        print(f"SAT instance generated and saved to tests/{filename}")

if __name__ == "__main__":
    main()