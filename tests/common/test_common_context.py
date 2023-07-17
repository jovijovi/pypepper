import pytest

from pypepper.common.context import context
from pypepper.common.utils.uuid import new_uuid_32bits


def test_new_context():
    # New context by default
    ctx1 = context.new()
    ctx1.context['key1'] = 'value1'
    value1 = ctx1.context.get('key1')
    print(f'Context({ctx1.context_id}) key1 -> {value1}')
    assert value1 == 'value1'

    # New context by id
    ctx2 = context.new(context_id='42')
    ctx2.context['key2'] = 'value2'
    value2 = ctx2.context.get('key2')
    print(f'Context({ctx2.context_id}) key2 -> {value2}')
    assert value2 == 'value2'

    # New child context
    ctx3 = context.new(parent=ctx2, context_id='43')
    ctx3.with_value('key3', 'value3')
    value3 = ctx3.context.get('key3')
    print(f'Context({ctx3.context_id}) key3 -> {value3}')
    parent_value2 = ctx3.parent.context.get('key2')
    print(f"Context({ctx3.context_id})'s parent({ctx3.parent.context_id}) key2 -> {parent_value2}")
    assert value3 == 'value3'
    assert parent_value2 == 'value2'


def test_born_chain():
    # Born 1st generation
    ctx5 = context.born(
        length=5,
        id_provider=new_uuid_32bits,
    )

    for i in range(5):
        context_id = ctx5.trace(i).context_id
        print(f'index={i}, context_id={context_id}')

    chain_head = ctx5.head()
    print("Chain head=", ctx5.head().context_id)
    print("Chain tail=", ctx5.context_id)

    # Born 2nd generation
    ctx10 = context.born(
        length=10,
        parent=ctx5,
    )

    for i in range(5):
        i += 5
        context_id = ctx10.trace(i).context_id
        print(f'index={i}, context_id={context_id}')

    print("Chain head=", ctx10.trace(0).context_id)
    print("Chain tail=", ctx10.context_id)
    assert chain_head.context_id == ctx10.head().context_id

    # Born the next one
    ctx11 = context.born(
        length=ctx10.length() + 1,
        parent=ctx10,
    )

    for i in range(1):
        i += 10
        context_id = ctx11.trace(i).context_id
        print(f'index={i}, context_id={context_id}')

    print("Chain head=", ctx11.head().context_id)
    print("Chain tail=", ctx11.context_id)
    assert chain_head.context_id == ctx11.head().context_id

    # A new chain fork
    ctx12 = context.born(
        length=ctx10.length() + 1,
        parent=ctx10,
    )
    print(f'index={10}, context_id={ctx12.trace(10).context_id}')
    print("Chain head=", ctx12.head().context_id)
    print("Chain tail=", ctx12.context_id)
    assert chain_head.context_id == ctx12.head().context_id


def test_get_chain_head():
    ctx = context.born(
        length=5,
    )
    print("Head=", ctx.head().context_id)
    print("Tail=", ctx.context_id)


if __name__ == '__main__':
    pytest.main()
