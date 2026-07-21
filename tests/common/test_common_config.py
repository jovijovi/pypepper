import pytest

from pypepper.common.config import config
from pypepper.scheduler.job import Job
from pypepper.scheduler.store import (
    configure_job_store,
    get_job_store,
    reset_job_store,
    set_job_store,
    setup_from_config,
)
from pypepper.scheduler.store.interfaces import IJobStore, JobRecord
from pypepper.scheduler.store.memory import InMemoryJobStore


def _write_durable_cfg(tmp_path, name: str = "durable-jobstore.yaml"):
    cfg = tmp_path / name
    cfg.write_text(
        "scheduler:\n"
        "  jobStore:\n"
        "    backend: postgres\n"
        "    uri: postgresql+psycopg://postgres:example@localhost:5432/mock_pypepper\n"
    )
    return cfg


def _restore_memory_config() -> None:
    """Avoid leaving durable YAML in the process-wide config for later tests."""
    config.load_config("./conf/app.config.yaml")
    config.mark_scheduler_job_store_applied()


class _NonMemoryStore(IJobStore):
    """Minimal non-InMemory store for deferred / configure-before-load tests."""

    def __init__(self) -> None:
        self._rows: dict[str, JobRecord] = {}

    def put(self, record: JobRecord) -> None:
        existing = self._rows.get(record.id)
        if existing is not None:
            record = JobRecord(
                id=record.id,
                category=record.category,
                channel_id=record.channel_id,
                status=record.status,
                created=existing.created,
                updated=record.updated,
                workflow_count=record.workflow_count,
                version=record.version,
            )
        self._rows[record.id] = record

    def get(self, job_id: str) -> JobRecord | None:
        return self._rows.get(job_id)

    def delete(self, job_id: str) -> None:
        self._rows.pop(job_id, None)

    def list(self, channel_id: str | None = None) -> list[JobRecord]:
        rows = list(self._rows.values())
        if channel_id is None:
            return rows
        return [r for r in rows if r.channel_id == channel_id]

    def clear(self) -> None:
        self._rows.clear()


def test_load_config():
    config.load_config("./conf/app.config.yaml")
    result = config.get_yml_config()
    assert result is not None
    assert result.network.httpServer.port == 55550
    assert result.log.level == "TRACE"
    assert result.sse.maxTotalConnections == 100
    assert list(result.sse.authentication.validKeys) == []


def test_config_setting_is_instance_isolated():
    from pypepper.common.config import Config

    c1 = Config()
    c2 = Config()
    marker = object()
    c1._setting = marker
    assert c2._setting is None
    assert c1.get_yml_config() is marker
    assert c2.get_yml_config() is None


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

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))

        assert calls == []
        assert isinstance(get_job_store(), InMemoryJobStore)
        with pytest.raises(ValueError, match="setup_from_config"):
            Job().save()
        with pytest.raises(ValueError, match="setup_from_config"):
            Job.get_saved("any-id")
    finally:
        _restore_memory_config()


def test_durable_job_store_ok_after_configure(tmp_path, monkeypatch):
    """Real configure clears deferred (no stub that self-marks)."""
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        with pytest.raises(ValueError, match="setup_from_config"):
            Job().save()

        configure_job_store("memory")
        assert len(warns) == 1
        assert "in-memory job store" in warns[0]
        assert "postgres" in warns[0]
        assert config._deferred_durable_job_store_backend is None

        configure_job_store("memory")
        assert len(warns) == 1

        job = Job()
        job.save()
        assert Job.get_saved(job.id) is not None
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_durable_yaml_set_job_store_memory_warns_once(tmp_path, monkeypatch):
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        set_job_store(InMemoryJobStore())
        assert len(warns) == 1
        assert config._deferred_durable_job_store_backend is None
        Job().save()
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_reset_job_store_does_not_emit_mismatch_warn(tmp_path, monkeypatch):
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        reset_job_store()
        assert warns == []
        assert config._deferred_durable_job_store_backend == "postgres"
        with pytest.raises(ValueError, match="setup_from_config"):
            Job().save()
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_memory_yaml_configure_memory_does_not_warn(tmp_path, monkeypatch):
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = tmp_path / "memory-jobstore.yaml"
    cfg.write_text("scheduler:\n  jobStore:\n    backend: memory\n")
    try:
        config.load_config(str(cfg))
        configure_job_store("memory")
        assert warns == []
        Job().save()
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_yaml_declared_backend_early_returns(monkeypatch):
    """Cover _yaml_declared_job_store_backend guard paths (patch coverage)."""
    from types import SimpleNamespace

    import pypepper.scheduler.store as store_mod

    monkeypatch.setattr(config, "get_yml_config", lambda: None)
    assert store_mod._yaml_declared_job_store_backend() is None

    monkeypatch.setattr(config, "get_yml_config", lambda: SimpleNamespace())
    assert store_mod._yaml_declared_job_store_backend() is None

    monkeypatch.setattr(config, "get_yml_config", lambda: SimpleNamespace(scheduler=None))
    assert store_mod._yaml_declared_job_store_backend() is None

    monkeypatch.setattr(
        config,
        "get_yml_config",
        lambda: SimpleNamespace(scheduler=SimpleNamespace(jobStore=None)),
    )
    assert store_mod._yaml_declared_job_store_backend() is None

    monkeypatch.setattr(
        config,
        "get_yml_config",
        lambda: SimpleNamespace(
            scheduler=SimpleNamespace(jobStore=SimpleNamespace(backend=None))
        ),
    )
    assert store_mod._yaml_declared_job_store_backend() is None

    monkeypatch.setattr(
        config,
        "get_yml_config",
        lambda: SimpleNamespace(
            scheduler=SimpleNamespace(jobStore=SimpleNamespace(backend="   "))
        ),
    )
    assert store_mod._yaml_declared_job_store_backend() is None


def test_durable_yaml_non_memory_store_does_not_warn(tmp_path, monkeypatch):
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        set_job_store(_NonMemoryStore())
        assert warns == []
        Job().save()
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_reset_clears_mismatch_warn_for_next_memory_install(tmp_path, monkeypatch):
    """reset_job_store clears one-shot so a later explicit memory install can warn again."""
    import pypepper.scheduler.store as store_mod
    from pypepper.common.log import log

    store_mod.reset_job_store_mismatch_warning()
    warns: list[str] = []
    monkeypatch.setattr(log, "warn", lambda msg, *a, **k: warns.append(str(msg)))

    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        configure_job_store("memory")
        assert len(warns) == 1

        reset_job_store()
        assert config._deferred_durable_job_store_backend == "postgres"

        configure_job_store("memory")
        assert len(warns) == 2
        Job().save()
    finally:
        store_mod.reset_job_store_mismatch_warning()
        _restore_memory_config()


def test_durable_job_store_ok_after_setup_from_config(tmp_path, monkeypatch):
    """setup_from_config → configure_job_store clears deferred via set_job_store."""
    cfg = _write_durable_cfg(tmp_path)
    import pypepper.scheduler.store as store_mod

    def _fake_configure(backend, **kwargs):
        assert backend == "postgres"
        store = _NonMemoryStore()
        store_mod.set_job_store(store)
        return store

    monkeypatch.setattr(store_mod, "configure_job_store", _fake_configure)
    try:
        config.load_config(str(cfg))
        setup_from_config(config.get_yml_config())
        assert config._deferred_durable_job_store_backend is None
        Job().save()
    finally:
        _restore_memory_config()


def test_configure_before_load_does_not_false_positive(tmp_path):
    """Non-memory store already installed: durable load must not block save."""
    set_job_store(_NonMemoryStore())
    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        assert config._deferred_durable_job_store_backend == "postgres"
        job = Job()
        job.save()
        assert Job.get_saved(job.id) is not None
        assert config._deferred_durable_job_store_backend is None
    finally:
        _restore_memory_config()


def test_reload_after_setup_clears_when_non_memory_installed(tmp_path):
    set_job_store(_NonMemoryStore())
    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        Job().save()
        config.load_config(str(cfg))
        Job().save()
    finally:
        _restore_memory_config()


def test_set_job_store_clears_deferred(tmp_path):
    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        set_job_store(InMemoryJobStore())
        assert config._deferred_durable_job_store_backend is None
        Job().save()
    finally:
        _restore_memory_config()


def test_reset_job_store_rearms_deferred_fail_fast(tmp_path):
    """reset must not allow silent memory persist while YAML still declares durable."""
    cfg = _write_durable_cfg(tmp_path)
    try:
        config.load_config(str(cfg))
        configure_job_store("memory")
        Job().save()

        reset_job_store()
        assert config._deferred_durable_job_store_backend == "postgres"
        with pytest.raises(ValueError, match="setup_from_config"):
            Job().save()
        with pytest.raises(ValueError, match="setup_from_config"):
            Job.get_saved("x")
    finally:
        _restore_memory_config()


def test_load_config_memory_job_store_does_not_defer():
    config.load_config("./conf/app.config.yaml")
    assert config._deferred_durable_job_store_backend is None
    Job().save()
