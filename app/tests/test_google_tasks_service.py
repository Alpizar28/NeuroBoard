from app.services.google_tasks_service import resolve_google_tasklist_id


def test_resolves_known_tasklist_name() -> None:
    assert resolve_google_tasklist_id("Proyectos")


def test_falls_back_to_default_for_unknown_name() -> None:
    assert resolve_google_tasklist_id("Unknown") == "@default"
