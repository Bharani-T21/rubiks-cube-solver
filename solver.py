import pycuber as pc
from pycuber.solver import CFOPSolver
from pycuber.helpers import array_to_cubies
from collections import Counter

def solve_cube(cube_state_string):
    try:
        # Check if we have exactly 9 of each 6 colors
        color_counts = Counter(cube_state_string)
        if len(color_counts) != 6 or any(count != 9 for count in color_counts.values()):
            counts_str = ", ".join(f"{count} {color}" for color, count in color_counts.items() if color != 'unknown')
            msg = f"Invalid color detection. Expected 9 squares per color, but found: {counts_str}."
            if 'unknown' in color_counts:
                msg += f" Unrecognized colors detected ({color_counts['unknown']})."
            msg += " Please check lighting and ensure no glare on the photos."
            return {"success": False, "error": msg, "details": "Color counting failed."}

        # pycuber expects a 54 char string or iterable: LUU... order: L, U, F, D, R, B
        cubies = array_to_cubies(cube_state_string)
        cube = pc.Cube(cubies)
        
        if not cube.is_valid():
             return {"success": False, "error": "Invalid cube state. Pieces are in an impossible configuration. Make sure you took photos of the correct faces in the correct orientation.", "details": "Cube failing is_valid() check."}

        solver = CFOPSolver(cube)
        solution = solver.solve()
        return {"success": True, "solution": [str(step) for step in solution]}
    except Exception as e:
        return {"success": False, "error": "Invalid cube state. Please check if the colors are detected correctly and the cube is valid.", "details": str(e)}
