from risk import calculate_rainfall_score, calculate_slope_score, calculate_risk


def test_rainfall_score_zero():
    assert calculate_rainfall_score(0, 0, 0, 0) == 0


def test_slope_score():
    assert calculate_slope_score(38) == 90
    assert calculate_slope_score(45) == 100


def test_risk_level_is_valid():
    result = calculate_risk(0, 0, 0, 0, 38)
    assert result["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert 0 <= result["risk_score"] <= 100
