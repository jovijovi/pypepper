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


if __name__ == '__main__':
    pytest.main()
