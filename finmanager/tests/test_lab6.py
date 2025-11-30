from core.domain import Account, Budget, Transaction
from core.frp import Event, StateEventBus, check_budget_handler, on_transaction_added


def test_event_bus_subscribe_publish():
    bus = StateEventBus()

    # Simple handler
    def handler(evt, state):
        return {**state, "count": state.get("count", 0) + 1}

    bus.subscribe("TEST", handler)

    state = {}
    evt = Event("1", "ts", "TEST", {})

    new_state = bus.publish(evt, state)
    assert new_state["count"] == 1


def test_transaction_added_handler():
    acc = Account("a1", "n", 1000, "c")
    state = {"transactions": (), "accounts": (acc,)}

    t = Transaction("t1", "a1", "c1", -100, "ts", "n")
    evt = Event("e1", "ts", "TRANSACTION_ADDED", {"transaction": t})

    new_state = on_transaction_added(evt, state)

    assert len(new_state["transactions"]) == 1
    # Check balance update: 1000 + (-100) = 900
    assert new_state["accounts"][0].balance == 900


def test_check_budget_handler():
    b = Budget("b1", "c1", 50, "m")
    t1 = Transaction("t1", "a1", "c1", -60, "ts", "n")  # Exceeds 50
    state = {"budgets": (b,), "transactions": (t1,), "alerts": []}

    evt = Event("e1", "ts", "TRANSACTION_ADDED", {"transaction": t1})

    new_state = check_budget_handler(evt, state)

    assert len(new_state["alerts"]) == 1
    assert "exceeded" in new_state["alerts"][0]

def test_event_bus_no_subscribers():
    bus = StateEventBus()
    state = {"count": 0}
    evt = Event("1", "ts", "TEST_NO_SUB", {})
    
    # Should not crash and return state as is
    new_state = bus.publish(evt, state)
    assert new_state["count"] == 0

def test_event_bus_multiple_subscribers():
    bus = StateEventBus()
    
    def h1(evt, state):
        return {**state, "h1": True}
    def h2(evt, state):
        return {**state, "h2": True}
        
    bus.subscribe("MULTI", h1)
    bus.subscribe("MULTI", h2)
    
    state = {}
    evt = Event("1", "ts", "MULTI", {})
    
    new_state = bus.publish(evt, state)
    assert new_state.get("h1") is True
    assert new_state.get("h2") is True
