import pytest


@pytest.mark.django_db(transaction=True)
class TestAdminLogin:

    def test_login(self, page, live_server):
        """Comprova que l'administrador pot iniciar sessió correctament."""
        page.goto(f"{live_server.url}/admin/login/")
        page.fill("#id_username", "isard")
        page.fill("#id_password", "pirineus")
        page.click("[type=submit]")

        assert page.url == f"{live_server.url}/admin/"

    def test_login_error(self, page, live_server):
        """Comprova que credencials incorrectes no permeten l'accés."""
        page.goto(f"{live_server.url}/admin/login/")
        page.fill("#id_username", "isard")
        page.fill("#id_password", "contrasenya_incorrecta")
        page.click("[type=submit]")

        assert page.url != f"{live_server.url}/admin/"
