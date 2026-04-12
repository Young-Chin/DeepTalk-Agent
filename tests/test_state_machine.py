from app.memory.session_store import SessionStore
from app.state_machine import ConversationStateMachine, State


def test_interrupt_during_speaking_switches_to_listening():
    memory = SessionStore()
    machine = ConversationStateMachine(memory=memory)

    machine.state = State.SPEAKING
    machine.on_interrupt()

    assert machine.state == State.LISTENING


def test_playback_finished_persists_agent_turn():
    memory = SessionStore()
    machine = ConversationStateMachine(memory=memory)

    machine.on_agent_reply_ready("追问：你最难忘的一次采访是什么？")
    machine.on_playback_finished()

    assert memory.snapshot()[-1]["role"] == "assistant"
