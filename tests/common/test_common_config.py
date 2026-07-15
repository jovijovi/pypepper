from pypepper.common.config import config
from pypepper.scheduler.store import get_job_store, reset_job_store
from pypepper.scheduler.store.memory import InMemoryJobStore


def test_load_config():
    config.load_config("./conf/app.config.yaml")
    result = config.get_yml_config()
    assert result is not None
    assert result.network.httpServer.port == 55550
    assert result.log.level == "TRACE"
    assert result.sse.maxTotalConnections == 100
    assert list(result.sse.authentication.validKeys) == []


def test_load_config_does_not_configure_job_store():
    """common.config must not import or call scheduler.store (layering)."""
    import pypepper.common.config as config_mod

    assert "scheduler.store" not in open(config_mod.__file__).read()

    reset_job_store()
    config.load_config("./conf/app.config.yaml")
    assert isinstance(get_job_store(), InMemoryJobStore)
    # YAML may declare scheduler.jobStore; apps must call setup_from_config explicitly.
    assert config.get_yml_config().scheduler is not None
