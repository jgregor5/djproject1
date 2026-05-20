import os
import pytest

os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):
    with django_db_blocker.unblock():
        from django.test.utils import setup_databases
        from django.core.management import call_command
        setup_databases(verbosity=0, interactive=False)
        call_command("loaddata", "myapp/fixtures/testdb.json")
