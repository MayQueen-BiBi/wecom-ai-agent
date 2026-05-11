from app.guards.dependency_guard import check_dependency_graph, scan_dependency_violations


def test_dependency_guard_passes() -> None:
    assert check_dependency_graph() is True
    assert scan_dependency_violations() == []
