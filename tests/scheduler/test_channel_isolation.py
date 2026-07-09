import pytest

from pypepper.scheduler import channel


@pytest.mark.asyncio
async def test_channel_stop_is_per_instance():
    c1 = channel.new()
    c2 = channel.new()
    c1.stop = True
    assert c2.stop is False


def test_channel_manager_is_singleton():
    m1 = channel.ChannelManager()
    m2 = channel.ChannelManager()
    assert m1 is m2
    assert m1 is channel.manager
