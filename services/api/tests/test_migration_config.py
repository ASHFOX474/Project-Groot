import pytest

from app.migrations import config, head_revision, postgres_url
from app import migrations, seed_demo


def test_single_migration_head():
    assert head_revision() == "0005"
    assert config().get_main_option("script_location").endswith("/migrations")


def test_url_uses_psycopg_and_preserves_escaped_password():
    url = postgres_url("postgresql://user:p%25ss@db/groot")
    assert url.drivername == "postgresql+psycopg"
    assert url.password == "p%ss"


@pytest.mark.parametrize("value", ["", "sqlite:///test.db", "not-a-url"])
def test_invalid_database_urls_are_rejected(value):
    with pytest.raises(ValueError, match="PostgreSQL DATABASE_URL"):
        postgres_url(value)


def test_cli_redacts_unexpected_errors(monkeypatch, capsys):
    def fail(*args, **kwargs):
        raise Exception("sensitive database URL and row contents")
    monkeypatch.setattr(migrations, "run", fail)
    assert migrations.main(["upgrade"]) == 1
    assert "sensitive" not in capsys.readouterr().err
    monkeypatch.setattr(seed_demo, "seed_demo", fail)
    assert seed_demo.main() == 1
    assert "sensitive" not in capsys.readouterr().err


def test_seed_cli_reports_guard_and_success(monkeypatch, capsys):
    def refuse(*args):
        raise RuntimeError("not at migration head")
    monkeypatch.setattr(seed_demo, "seed_demo", refuse)
    assert seed_demo.main() == 1
    assert "not at migration head" in capsys.readouterr().err
    monkeypatch.setattr(seed_demo, "seed_demo", lambda *args: None)
    assert seed_demo.main() == 0
    assert "not overwritten" in capsys.readouterr().out
