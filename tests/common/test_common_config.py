import pytest

from pypepper.common.config import config
from pypepper.common.log import log
from pypepper.scheduler.job import Job
from pypepper.scheduler.store import get_job_store, reset_job_store, setup_from_config
from pypepper.scheduler.store.memory import InMemoryJobStore


def test_load_config():
    config.load_config("./conf/app.config.yaml")
    result = config.get_yml_config()
    assert result is not None
    assert result.network.httpServer.port == 55550
    assert result.log.level == "TRACE"
    assert result.sse.maxTotalConnections == 100
    assert list(result.sse.authentication.validKeys) == []


def test_load_config_does_not_configure_job_store(monkeypatch, tmp_path):
    """common.config must not import or call scheduler.store (layering)."""
    import pypepper.common.config as config_mod
    import pypepper.scheduler.store as store_mod

    src = open(config_mod.__file__).read()
    assert "from pypepper.scheduler.store" not in src
    assert "import pypepper.scheduler.store" not in src

    calls: list[str] = []
    monkeypatch.setattr(
        store_mod,
        "setup_from_config",
        lambda *a, **k: calls.append("setup_from_config"),
    )
    monkeypatch.setattr(
        store_mod,
        "configure_job_store",
        lambda *a, **k: calls.append("configure_job_store"),
    )

    cfg = tmp_path / "durable-jobstore.yaml"
    cfg.write_text(
        "scheduler:\n"
        "  jobStore:\n"
        "    backend: postgres\n"
        "    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper\n"
    )

    reset_job_store()
    config.mark_scheduler_job_store_applied()
    config.load_config(str(cfg))

    assert calls == []
    assert isinstance(get_job_store(), InMemoryJobStore)
    with pytest.raises(ValueError, match="setup_from_config"):
        Job().save()


def test_durable_job_store_ok_after_setup(tmp_path, monkeypatch):
    cfg = tmp_path / "durable-jobstore.yaml"
    cfg.write_text(
        "scheduler:\n"
        "  jobStore:\n"
        "    backend: postgres\n"
        "    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper\n"
    )
    reset_job_store()
    config.mark_scheduler_job_store_applied()
    config.load_config(str(cfg))

    import pypepper.scheduler.store as store_mod

    def _fake_configure(backend, **kwargs):
        store_mod.set_job_store(InMemoryJobStore())
        config.mark_scheduler_job_store_applied()
        return store_mod.get_job_store()

    monkeypatch.setattr(store_mod, "configure_job_store", _fake_configure)
    setup_from_config(config.get_yml_config())
    Job().save()


def test_load_config_memory_job_store_does_not_defer(monkeypatch):
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))
    reset_job_store()
    config.mark_scheduler_job_store_applied()
    config.load_config("./conf/app.config.yaml")
    assert config._deferred_durable_job_store_backend is None
    assert not any("jobStore" in w for w in warns)
    Job().save()
