from app.services.google_tasks_service import GoogleTasksService, resolve_google_tasklist_id


def test_resolves_known_tasklist_name() -> None:
    assert resolve_google_tasklist_id("Proyectos")


def test_falls_back_to_default_for_unknown_name() -> None:
    assert resolve_google_tasklist_id("Unknown") == "@default"


def test_detects_refresh_credentials() -> None:
    service = GoogleTasksService(
        "",
        refresh_token="refresh-token",
        client_id="client-id",
        client_secret="client-secret",
    )

    assert service._has_refresh_credentials() is True
