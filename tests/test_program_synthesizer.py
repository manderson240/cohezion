import pytest
import numpy as np
from cohezion.agi.program_synthesizer import synthesize_closed_loop_program

def test_identity_synthesis():
    p1 = ([[1, 2], [3, 4]], [[1, 2], [3, 4]])
    p2 = ([[5, 6], [7, 8]], [[5, 6], [7, 8]])
    p3 = ([[0, 1], [2, 3]], [[0, 1], [2, 3]])
    prog = synthesize_closed_loop_program([p1, p2, p3])
    assert prog is not None
    assert prog.name == 'Identity'
    assert prog([[9, 9], [9, 9]]) == [[9, 9], [9, 9]]

def test_d4_rotation_synthesis():
    # 90 degree clockwise rotation
    x1 = [[1, 2], [3, 4]]
    y1 = [[3, 1], [4, 2]]
    x2 = [[5, 6], [7, 8]]
    y2 = [[7, 5], [8, 6]]
    x3 = [[0, 9], [1, 2]]
    y3 = [[1, 0], [2, 9]]
    prog = synthesize_closed_loop_program([(x1, y1), (x2, y2), (x3, y3)])
    assert prog is not None
    assert 'D4' in prog.name
    test_in = [[2, 0], [0, 1]]
    assert prog(test_in) == [[0, 2], [1, 0]]

def test_color_substitution_synthesis():
    # Swap color 1 to 2, 3 to 4
    x1 = [[1, 1], [3, 0]]
    y1 = [[2, 2], [4, 0]]
    x2 = [[1, 3], [3, 1]]
    y2 = [[2, 4], [4, 2]]
    x3 = [[3, 3], [1, 0]]
    y3 = [[4, 4], [2, 0]]
    prog = synthesize_closed_loop_program([(x1, y1), (x2, y2), (x3, y3)])
    assert prog is not None
    assert 'ColorMap' in prog.name
    assert prog([[1, 0], [3, 1]]) == [[2, 0], [4, 2]]

def test_gravity_synthesis():
    # Downward gravity
    x1 = [[1, 0], [0, 2]]
    y1 = [[0, 0], [1, 2]]
    x2 = [[3, 4], [0, 0]]
    y2 = [[0, 0], [3, 4]]
    x3 = [[0, 5], [6, 0]]
    y3 = [[0, 0], [6, 5]]
    prog = synthesize_closed_loop_program([(x1, y1), (x2, y2), (x3, y3)])
    assert prog is not None
    assert 'Gravity' in prog.name
    assert prog([[7, 0], [0, 8]]) == [[0, 0], [7, 8]]

def test_small_degenerate_rejection():
    # Single pair or degenerate should reject to prevent overfit
    x1 = [[1]]
    y1 = [[2]]
    prog = synthesize_closed_loop_program([(x1, y1)])
    assert prog is None
