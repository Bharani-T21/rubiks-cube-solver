import pycuber as pc
from pycuber.solver import CFOPSolver
import random
import time
import sys

# Perform a few random tests
print("Testing random valid cubes to see if CFOPSolver hangs...")
for i in range(10):
    c = pc.Cube()
    # scramble with 20 random moves
    moves = ["R", "R'", "R2", "L", "L'", "L2", "U", "U'", "U2", "D", "D'", "D2", "F", "F'", "F2", "B", "B'", "B2"]
    scramble = [random.choice(moves) for _ in range(20)]
    algo = pc.Formula(" ".join(scramble))
    c(algo)
    
    print(f"Test {i+1} - Start solving...")
    start_time = time.time()
    try:
        solver = CFOPSolver(c)
        sol = solver.solve()
        elapsed = time.time() - start_time
        print(f"Test {i+1} - Solved in {elapsed:.2f} seconds. Steps: {len(sol)}")
    except Exception as e:
        print(f"Test {i+1} - Exception: {e}")
