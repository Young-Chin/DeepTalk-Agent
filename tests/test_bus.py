import pytest

from app.bus import Event, EventBus, EventType


@pytest.mark.asyncio
async def test_bus_delivers_events_in_order():
    bus = EventBus()

    await bus.publish(Event(type=EventType.USER_FINAL_TEXT, payload={"text": "你好"}))
    await bus.publish(Event(type=EventType.AGENT_TEXT_READY, payload={"text": "欢迎"}))

    items = [await bus.next_event(), await bus.next_event()]
    assert [item.type for item in items] == [
        EventType.USER_FINAL_TEXT,
        EventType.AGENT_TEXT_READY,
    ]
