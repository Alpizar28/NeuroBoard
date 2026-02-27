from app.services.classification_service import classify_task


def test_course_prefix_goes_to_proyectos() -> None:
    result = classify_task("SUPERIOR: Exam viernes")
    assert result.list_name == "Proyectos"
    assert result.confidence >= 0.9


def test_project_prefix_goes_to_jokem() -> None:
    result = classify_task("JOKEM OS: Fix deploy issue")
    assert result.list_name == "Jokem"
    assert result.confidence >= 0.9


def test_no_prefix_falls_back_to_domesticas() -> None:
    result = classify_task("Lavar ropa")
    assert result.list_name == "Domesticas"
    assert "No prefix" in result.reason


def test_jp_prefix_goes_to_personales() -> None:
    result = classify_task("JP: Rutina gym manana")
    assert result.list_name == "Personales"
