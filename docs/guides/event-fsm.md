# Event and FSM

## Event

Create, sign, verify, and marshal events with stable JSON canonical bytes.

```python
from pypepper.common.security.crypto.elliptic.ecdsa import ecdsa
from pypepper.event import event as event_mod

private_key = ecdsa.new_key_pair()
private_pem = ecdsa.get_private_key_pem(private_key)
public_pem = ecdsa.get_public_key_pem(private_key)

evt = event_mod.new(name="order.created", src="checkout")
evt.add_payload(payload_id="p1", category="json", raw=b'{"id":1}', hash_alg="sha256")
evt.sign(private_pem, "sha256")
assert evt.verify(public_pem, "sha256")
print(evt.marshal())
```

!!! note
    Signatures use canonical JSON. Older pickle-based signatures will not verify.

## FSM

Build a machine with `Options` + `Transition`, then trigger events with `on()`.

```python
from pypepper.event import event as event_mod
from pypepper.fsm import fsm

idle = fsm.State("idle")
running = fsm.State("running")
done = fsm.State("done")

start = event_mod.new(name="start")
finish = event_mod.new(name="finish")

machine = fsm.new(
    fsm.Options(
        fsm_id="demo",
        initial=idle,
        transitions=[
            fsm.Transition(event=start, from_state=[idle], to_state=running),
            fsm.Transition(event=finish, from_state=[running], to_state=done),
        ],
    )
)

assert machine.current().value == "idle"
machine.on(start)
assert machine.current().value == "running"
machine.on(finish)
assert machine.current().value == "done"
```

### Rollback

If a transition handler or caller handler raises, the previous state is restored and the error is returned on `Response.error`.

```python
def boom():
    raise RuntimeError("handler failed")

resp = machine.on(start, handler=boom)
assert resp.error is not None
# state rolled back to the previous value
```

Unknown transitions return `Response.error` without raising.

See also: [API Reference / Event and FSM](../reference/event-fsm.md).
