from cohezion.kaggle.arc_bitboard import ArcBitboard


def test_bitboard_roundtrip():
    grid = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7, 8],
    ]
    bb = ArcBitboard.from_grid(grid)
    reconstructed = bb.to_grid()
    assert reconstructed == grid
    assert bb.height == 3
    assert bb.width == 3


def test_color_counts_and_presence():
    grid = [
        [1, 1, 0],
        [0, 2, 2],
        [0, 2, 0],
    ]
    bb = ArcBitboard.from_grid(grid)
    assert bb.color_count(1) == 2
    assert bb.color_count(2) == 3
    assert bb.color_count(0) == 4
    assert bb.color_count(5) == 0
    assert bb.has_color(1) is True
    assert bb.has_color(5) is False
    assert bb.color_counts() == {0: 4, 1: 2, 2: 3}


def test_bounding_box():
    grid = [
        [0, 0, 0, 0],
        [0, 3, 0, 0],
        [0, 3, 3, 0],
        [0, 0, 0, 0],
    ]
    bb = ArcBitboard.from_grid(grid)
    bbox = bb.bounding_box(3)
    # y: 1 to 2, x: 1 to 2
    assert bbox == (1, 2, 1, 2)
    assert bb.bounding_box(4) is None


def test_translation():
    grid = [
        [1, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]
    bb = ArcBitboard.from_grid(grid)
    translated = bb.translate(dy=1, dx=2)
    expected = [
        [0, 0, 0],
        [0, 0, 1],
        [0, 0, 0],
    ]
    assert translated.to_grid() == expected


def test_reflections_and_rotation():
    grid = [
        [1, 2],
        [3, 4],
    ]
    bb = ArcBitboard.from_grid(grid)
    assert bb.reflect_v().to_grid() == [
        [3, 4],
        [1, 2],
    ]
    assert bb.reflect_h().to_grid() == [
        [2, 1],
        [4, 3],
    ]
    # 90 clockwise:
    # [1, 2] -> [3, 1]
    # [3, 4]    [4, 2]
    assert bb.rotate90().to_grid() == [
        [3, 1],
        [4, 2],
    ]


def test_d4_symmetries_group_order():
    grid = [
        [1, 2, 0],
        [0, 3, 0],
        [0, 0, 4],
    ]
    bb = ArcBitboard.from_grid(grid)
    symmetries = bb.d4_symmetries()
    assert len(symmetries) == 8
    # Rotate 360 must return to origin
    assert bb.rotate90().rotate90().rotate90().rotate90().to_grid() == grid


def test_overlap_calculation():
    grid1 = [
        [1, 1, 0],
        [0, 2, 2],
    ]
    grid2 = [
        [1, 0, 0],
        [0, 2, 0],
    ]
    bb1 = ArcBitboard.from_grid(grid1)
    bb2 = ArcBitboard.from_grid(grid2)
    assert bb1.overlap_area(bb2, color=1) == 1
    assert bb1.overlap_area(bb2, color=2) == 1
    # color 0 matches at (0, 2) and (1, 0), color 1 matches at (0, 0), color 2 matches at (1, 1) -> total 4
    assert bb1.total_overlap(bb2) == 4
