from lib.data_health import compute_full_health, MAINTENANCE_ACTIONS


def test_compute_full_health_returns_dict():
    result = compute_full_health()
    assert "table_freshness" in result
    assert "global_health" in result


def test_maintenance_actions_dict_not_empty():
    assert len(MAINTENANCE_ACTIONS) >= 3