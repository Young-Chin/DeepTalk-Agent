from app.memory.session_store import SessionStore


def test_session_store_keeps_recent_turns():
    store = SessionStore(max_turns=2)

    store.add_user_turn("A")
    store.add_agent_turn("B", interrupted=False)
    store.add_user_turn("C")

    snapshot = store.snapshot()
    assert len(snapshot) == 2
    assert snapshot[-1]["content"] == "C"
