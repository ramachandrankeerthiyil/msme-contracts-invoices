"""AST-001 AC4 (Stop): a browser disconnect cancels the answer and closes the model stream."""

import asyncio

from app.api.chat import EventStreamResponse


def test_AST_001_AC4_disconnect_stops_the_answer_and_closes_the_stream():
    produced: list[str] = []
    closed = asyncio.Event()

    async def slow_answer():
        try:
            for i in range(100):
                yield f"event: text\ndata: {i}\n\n"
                await asyncio.sleep(0.01)
        finally:
            closed.set()  # where the Claude stream would be closed

    async def scenario():
        sent: list[dict] = []
        received = 0

        async def receive():
            nonlocal received
            received += 1
            await asyncio.sleep(0.05)  # the user presses Stop shortly after the answer starts
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)
            if message["type"] == "http.response.body" and message["body"]:
                produced.append(message["body"].decode())

        response = EventStreamResponse(slow_answer())
        await asyncio.wait_for(response({"type": "http"}, receive, send), timeout=2)
        return sent

    sent = asyncio.run(scenario())

    assert closed.is_set()
    assert 0 < len(produced) < 100
    assert sent[0]["type"] == "http.response.start"
    headers = dict(sent[0]["headers"])
    assert headers[b"cache-control"] == b"no-cache"
    assert headers[b"x-accel-buffering"] == b"no"
    assert headers[b"content-type"].startswith(b"text/event-stream")


def test_AST_001_AC4_a_finished_answer_completes_normally():
    async def short_answer():
        yield "event: done\ndata: {}\n\n"

    async def scenario():
        sent: list[dict] = []

        async def receive():
            await asyncio.sleep(10)  # the browser stays connected
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        await asyncio.wait_for(
            EventStreamResponse(short_answer())({"type": "http"}, receive, send), timeout=2
        )
        return sent

    sent = asyncio.run(scenario())

    assert sent[-1] == {"type": "http.response.body", "body": b"", "more_body": False}
