from backend.services.upload_utils import safe_filename


def test_safe_filename_strips_path_traversal() -> None:
    assert safe_filename("../../secret/report.pdf") == "report.pdf"


def test_safe_filename_strips_windows_separators() -> None:
    assert safe_filename("..\\..\\windows\\payload.docx") == "payload.docx"


def test_safe_filename_rejects_empty_result() -> None:
    try:
        safe_filename("../..")
    except ValueError as exc:
        assert str(exc) == "Invalid filename"
    else:
        raise AssertionError("Expected ValueError")