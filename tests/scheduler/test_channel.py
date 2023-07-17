import pytest

from pypepper.scheduler import channel
from pypepper.scheduler.channel import Channel

SEND_ROUND = 3
TOTAL_LENGTH = 2 * SEND_ROUND


@pytest.mark.asyncio
async def send(chan: Channel, num: int):
    for i in range(SEND_ROUND):
        await chan.send(f"{num}:{i}")


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
        await send(chan, num)

    print("Channel Length=", chan.length())


@pytest.mark.asyncio
async def test_channel():
    for i in range(2):
        chan = channel.new()
        await fill(chan)
        await receive(chan)

    print("Done")


if __name__ == '__main__':
    pytest.main()
