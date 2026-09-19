from terrain import calculate_slope_from_cross


def test_flat_terrain_is_zero():
    slope = calculate_slope_from_cross(25.0, 91.0, [100, 100, 100, 100, 100], 0.0015)
    assert slope == 0


def test_slope_is_bounded():
    slope = calculate_slope_from_cross(25.0, 91.0, [100, 200, 0, 100, 100], 0.0015)
    assert 0 <= slope <= 90
