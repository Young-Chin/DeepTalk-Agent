"""Performance benchmark for the main conversation pipeline."""
import asyncio
import time
import os
import pytest

os.environ["PODCAST_BACKEND"] = "mock"

from app.main import build_app, handle_event, pump_microphone_once, consume_next_event
from app.bus import Event, EventType


@pytest.fixture
def app():
    return build_app()


@pytest.mark.asyncio
async def test_benchmark_user_to_agent_pipeline(app):
    """Benchmark: User speaks -> ASR -> LLM -> TTS -> Playback"""
    results = {}

    # Push mock audio frames
    for _ in range(10):
        app["audio_in"].push_frame(b"test audio frame")

    t0 = time.perf_counter()
    await pump_microphone_once(app)
    asr_done = time.perf_counter()
    results["asr_latency_ms"] = int((asr_done - t0) * 1000)

    # Process agent response
    await consume_next_event(app)
    pipeline_done = time.perf_counter()
    results["full_pipeline_ms"] = int((pipeline_done - t0) * 1000)

    # Print results
    print(f"\n{'='*60}")
    print(f"PERFORMANCE BENCHMARK: User -> Agent Pipeline (Mock)")
    print(f"{'='*60}")
    print(f"  ASR transcription:     {results['asr_latency_ms']:>5} ms")
    print(f"  Full pipeline (ASR->LLM->TTS): {results['full_pipeline_ms']:>5} ms")
    print(f"{'='*60}")

    assert results["full_pipeline_ms"] < 5000, "Full pipeline should complete within 5s (mock)"


@pytest.mark.asyncio
async def test_benchmark_concurrent_turns(app):
    """Benchmark: Multiple conversation turns"""
    turns = 5
    start = time.perf_counter()

    for i in range(turns):
        for _ in range(10):
            app["audio_in"].push_frame(b"test audio frame")
        await pump_microphone_once(app)
        await consume_next_event(app)

    total_ms = int((time.perf_counter() - start) * 1000)
    avg_ms = total_ms // turns

    print(f"\n{'='*60}")
    print(f"PERFORMANCE BENCHMARK: {turns} Concurrent Turns (Mock)")
    print(f"{'='*60}")
    print(f"  Total time:            {total_ms:>5} ms")
    print(f"  Avg per turn:          {avg_ms:>5} ms")
    print(f"{'='*60}")

    assert avg_ms < 5000, "Avg turn latency should be under 5s (mock)"


@pytest.mark.asyncio
async def test_benchmark_event_bus_throughput(app):
    """Benchmark: Event bus message throughput"""
    bus = app["bus"]
    count = 1000

    async def publish_events():
        for i in range(count):
            await bus.publish(Event(type=EventType.INTERRUPT, payload={}))

    start = time.perf_counter()
    await publish_events()
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    print(f"\n{'='*60}")
    print(f"PERFORMANCE BENCHMARK: Event Bus Throughput")
    print(f"{'='*60}")
    print(f"  Events published:      {count:>5}")
    print(f"  Time:                  {elapsed_ms:>5} ms")
    print(f"  Throughput:            {count/max(elapsed_ms/1000, 0.001):>8.0f} events/sec")
    print(f"{'='*60}")


@pytest.mark.asyncio
async def test_benchmark_state_machine_transitions(app):
    """Benchmark: State machine transition speed"""
    sm = app["state_machine"]
    transitions = 10000

    start = time.perf_counter()
    for _ in range(transitions):
        sm.on_user_final_text("test")
        sm.on_interrupt()
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    avg_us = (elapsed_ms / transitions) * 1000

    print(f"\n{'='*60}")
    print(f"PERFORMANCE BENCHMARK: State Machine Transitions")
    print(f"{'='*60}")
    print(f"  Transitions:           {transitions:>6}")
    print(f"  Total time:            {elapsed_ms:>5} ms")
    print(f"  Avg per transition:    {avg_us:>8.2f} us")
    print(f"{'='*60}")

    assert avg_us < 100, "State machine transition should be < 100us"
