from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Check if kociemba is available (installed on Linux / Railway)
try:
    import kociemba
    HAS_KOCIEMBA = True
except ImportError:
    HAS_KOCIEMBA = False
    logger.warning("kociemba library not found. Will use pycuber as fallback.")

# pycuber fallback
import pycuber as pc
from pycuber.solver import CFOPSolver
from pycuber.helpers import array_to_cubies

# User-friendly messages for Kociemba error codes
KOCIEMBA_ERRORS = {
    "Error 1": "Color counting error. Make sure all 6 faces are scanned properly.",
    "Error 2": "Edge piece error. Some edge pieces are duplicate or missing.",
    "Error 3": "Orientation error: An edge piece appears flipped. Please check edge sticker colors.",
    "Error 4": "Corner piece error. Some corner pieces are duplicate or missing.",
    "Error 5": "Orientation error: A corner piece appears twisted. Please check corner sticker colors.",
    "Error 6": "Parity error: Two pieces appear swapped. Please double-check face colors.",
    "Error 7": "No solution found within the search depth.",
    "Error 8": "Solver timed out while calculating moves."
}

def convert_to_faces_dict(cube_input):
    """
    Normalizes cube input (dict or list) into a standardized dictionary:
    { 'up': [...], 'right': [...], 'front': [...], 'down': [...], 'left': [...], 'back': [...] }
    """
    if isinstance(cube_input, dict):
        return cube_input
    
    if isinstance(cube_input, (list, tuple)) and len(cube_input) == 54:
        # Expected pycuber/legacy order: left, up, front, down, right, back
        return {
            'left': list(cube_input[0:9]),
            'up': list(cube_input[9:18]),
            'front': list(cube_input[18:27]),
            'down': list(cube_input[27:36]),
            'right': list(cube_input[36:45]),
            'back': list(cube_input[45:54])
        }
    
    raise ValueError("Invalid cube input: Expected 54-sticker list or face dictionary.")

def build_kociemba_string(faces_colors):
    """
    Converts faces_colors into the 54-character Kociemba facelet string format:
    UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
    
    Kociemba face order: Up, Right, Front, Down, Left, Back (URFDLB).
    Facelet indices on each face are row-by-row (0 to 8).
    Center piece (index 4) on each face defines the identity of that face.
    """
    kociemba_faces = ['up', 'right', 'front', 'down', 'left', 'back']
    face_letters = {
        'up': 'U',
        'right': 'R',
        'front': 'F',
        'down': 'D',
        'left': 'L',
        'back': 'B'
    }

    # 1. Verify all 6 faces exist and have 9 stickers
    for face in kociemba_faces:
        if face not in faces_colors or len(faces_colors[face]) != 9:
            raise ValueError(f"Face '{face}' is missing or does not have exactly 9 stickers.")

    # 2. Check total color counts across all 54 stickers
    all_stickers = [c for f in kociemba_faces for c in faces_colors[f]]
    counts = Counter(all_stickers)
    if len(counts) != 6 or any(cnt != 9 for cnt in counts.values()):
        counts_str = ", ".join(f"{cnt} {c}" for c, cnt in counts.items())
        raise ValueError(f"Color validation failed. Expected 9 stickers per color, but found: {counts_str}.")

    # 3. Map center sticker (index 4) of each face to its Kociemba face character
    color_to_char = {}
    for face in kociemba_faces:
        center_color = faces_colors[face][4]
        if center_color in color_to_char:
            raise ValueError(
                f"Duplicate center color '{center_color}' found on face '{face}'. "
                "Each of the 6 faces must have a different center color."
            )
        color_to_char[center_color] = face_letters[face]

    # 4. Construct the 54-character Kociemba string (URFDLB order)
    kociemba_chars = []
    for face in kociemba_faces:
        for idx, color in enumerate(faces_colors[face]):
            if color not in color_to_char:
                raise ValueError(f"Unrecognized color '{color}' at face '{face}', sticker {idx+1}.")
            kociemba_chars.append(color_to_char[color])

    return "".join(kociemba_chars)

def solve_with_kociemba(cube_string):
    """
    Invokes kociemba.solve() and returns list of move tokens.
    """
    try:
        raw_solution = kociemba.solve(cube_string)
        if not raw_solution:
            return []
        # Return cleaned list of move tokens (e.g. ['R', 'U', "R'", 'F2'])
        return [m.strip() for m in raw_solution.split() if m.strip()]
    except Exception as e:
        err_str = str(e)
        for code, msg in KOCIEMBA_ERRORS.items():
            if code in err_str:
                raise ValueError(f"Kociemba validation error ({code}): {msg}")
        raise ValueError(f"Kociemba error: {err_str}")

def solve_with_pycuber(faces_colors):
    """
    Fallback solver using pycuber CFOPSolver.
    """
    # pycuber expects L, U, F, D, R, B order
    pycuber_order = ['left', 'up', 'front', 'down', 'right', 'back']
    legacy_list = [c for f in pycuber_order for c in faces_colors[f]]
    
    cubies = array_to_cubies(legacy_list)
    cube = pc.Cube(cubies)
    
    if not cube.is_valid():
        raise ValueError("Invalid cube state: Pieces are in an impossible configuration.")

    solver = CFOPSolver(cube)
    solution = solver.solve()
    return [str(step) for step in solution]

def solve_cube(cube_input):
    """
    Main entry point for solving the Rubik's cube.
    Uses Kociemba Two-Phase algorithm when available (optimal ~20 moves),
    with fallback to pycuber CFOP if kociemba is not installed locally.
    """
    try:
        faces_colors = convert_to_faces_dict(cube_input)
        
        # Check basic color counting first
        all_stickers = [c for face_list in faces_colors.values() for c in face_list]
        counts = Counter(all_stickers)
        if len(counts) != 6 or any(cnt != 9 for cnt in counts.values()):
            counts_str = ", ".join(f"{cnt} {c}" for c, cnt in counts.items())
            return {
                "success": False,
                "error": f"Invalid color detection. Expected 9 stickers per color, but found: {counts_str}.",
                "details": "Color counting failed."
            }

        # Build Kociemba 54-char string: UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
        kociemba_string = build_kociemba_string(faces_colors)
        
        # Check if already solved
        solved_kociemba_string = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"
        if kociemba_string == solved_kociemba_string:
            return {
                "success": True,
                "solution": [],
                "move_count": 0,
                "algorithm": "kociemba",
                "kociemba_string": kociemba_string
            }

        if HAS_KOCIEMBA:
            moves = solve_with_kociemba(kociemba_string)
            return {
                "success": True,
                "solution": moves,
                "move_count": len(moves),
                "algorithm": "kociemba",
                "kociemba_string": kociemba_string
            }
        else:
            # Fallback to pycuber CFOP
            moves = solve_with_pycuber(faces_colors)
            return {
                "success": True,
                "solution": moves,
                "move_count": len(moves),
                "algorithm": "cfop_fallback",
                "kociemba_string": kociemba_string
            }

    except ValueError as ve:
        return {
            "success": False,
            "error": str(ve),
            "details": "Validation or state error."
        }
    except Exception as e:
        return {
            "success": False,
            "error": "Invalid cube state. Please verify the colors of each sticker.",
            "details": str(e)
        }
