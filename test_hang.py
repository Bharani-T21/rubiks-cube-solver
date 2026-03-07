import pycuber as pc
from pycuber.solver import CFOPSolver
import threading
import os

def terminate():
    print("Script terminated. Hang detected!")
    os._exit(0)

timer = threading.Timer(3.0, terminate)
timer.start()

c = pc.Cube()
c("R U R' U'")
cubie = c["UFL"]
old_u = cubie["U"]
old_f = cubie["F"]
old_l = cubie["L"]
cubie.facings = {"U": old_f, "F": old_l, "L": old_u}

print("Is valid?", c.is_valid())
print("Attempting to solve...")
try:
    solver = CFOPSolver(c)
    sol = solver.solve()
    print("Solved:")
    print(sol)
except Exception as e:
    print("Exception:")
    print(e)
finally:
    timer.cancel()
