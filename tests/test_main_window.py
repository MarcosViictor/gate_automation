from controllers.auth_controller import AccessDecision
from views.main_window import MainWindow


def test_format_status_authorized():
    d = AccessDecision(True, "TAG1", "IN", "Acesso liberado", online=True)
    assert MainWindow.format_status(d) == "AUTORIZADO"


def test_format_status_denied_with_reason():
    d = AccessDecision(False, "TAG1", "IN", "Tag inativa", online=True)
    assert MainWindow.format_status(d) == "NEGADO (Tag inativa)"


def test_format_status_denied_without_reason():
    d = AccessDecision(False, "TAG1", "IN", None, online=False)
    assert MainWindow.format_status(d) == "NEGADO"
