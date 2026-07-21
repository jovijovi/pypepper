import pytest

from pypepper.scheduler import channel
from pypepper.scheduler.channel import Channel

SEND_ROUND = 3
TOTAL_LENGTH = 2 * SEND_ROUND


@pytest.mark.asyncio
async def send(chan: Channel, num: int):
    ret = False
    for i in range(SEND_ROUND):
        ret = await chan.send(f"{num}:{i}")
    return ret


@pytest.mark.asyncio
async def receive(chan):
    count = 0
    while not chan.stop:
        value = await chan.receive()
        print("Value=", value)
        count += 1
        if count == TOTAL_LENGTH:
            print("Channel closed")
            return


async def fill(chan: Channel):
    for num in range(2):
        ret = await send(chan, num)
        print(f"Send from {num} completed, ret={ret}")

    print("Channel Length=", chan.length())


@pytest.mark.asyncio
async def test_channel():
    for i in range(2):
        chan = channel.new()
        await fill(chan)
        await receive(chan)

    print("Done")


@pytest.mark.asyncio
async def test_channel_full():
    chan = channel.new(1)
    await fill(chan)


def test_channel_manager():
    manager = channel.manager

    ret = manager.get("NotExistJob")
    assert ret is None

    ret = manager.remove("NotExistJob")
    assert ret is None

    chan1 = channel.manager.available("job1")
    chan2 = channel.manager.available("job2")

    manager.put("job1", chan1)
    manager.put("job2", chan2)

    ret_chan1 = manager.get("job1")
    assert ret_chan1 is chan1

    ret_chan2 = manager.get("job2")
    assert ret_chan2 is chan2

    manager.remove("job1")
    ret_chan1_after = manager.get("job1")
    assert ret_chan1_after is None

    manager.remove("job2")
    ret_chan2_after = manager.get("job2")
    assert ret_chan2_after is None

    print("All channel removed")


@pytest.mark.asyncio
async def test_channel_manager_maxsize_applies_only_on_first_create():
    manager = channel.manager
    key = "bounded-once"
    manager.remove(key)

    bounded = manager.new(key, maxsize=1)
    again = manager.available(key, maxsize=0)
    assert again is bounded

    assert await bounded.send("a") is True
    assert await bounded.send("b") is False

    manager.remove(key)


@pytest.mark.asyncio
async def test_channel_manager_ignores_maxsize_after_unbounded_create():
    manager = channel.manager
    key = "unbounded-first"
    manager.remove(key)

    unbounded = manager.available(key)  # default maxsize=0
    again = manager.new(key, maxsize=1)
    assert again is unbounded

    assert await unbounded.send("a") is True
    assert await unbounded.send("b") is True

    manager.remove(key)


def test_channel_manager_new_maxsize_scheduled_raises_channel_full():
    import asyncio

    from pypepper.scheduler.job import ChannelFullError, Job

    manager = channel.manager
    channel_id = "mgr-new-bounded-full"
    manager.remove(channel_id)
    bounded = manager.new(channel_id, maxsize=1)
    assert asyncio.run(bounded.send("occupier")) is True
    try:
        job = Job(category="x", channel_id=channel_id)
        with pytest.raises(ChannelFullError, match="channel full"):
            job.scheduled()
    finally:
        manager.remove(channel_id)


if __name__ == '__main__':
    pytest.main()
