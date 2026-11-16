"""Backlog caps on the distill queue (issue #222).

The queue used to accept unbounded pending tasks; a saturated worker pool
meant unbounded wait and memory growth. submit() now raises QueueFullError
past a global cap and a per-device cap, which the endpoints map to 429.
"""

import asyncio
import unittest

from server.main import DistillTaskQueue, QueueFullError


def _payload(url: str, identity: str) -> dict:
    return {"url": url, "name": "n", "device_fingerprint": identity}


class QueueBacklogCapTests(unittest.TestCase):
    def test_global_pending_cap_rejects_new_submissions(self):
        async def scenario():
            queue = DistillTaskQueue(worker_count=1, max_pending=2, max_pending_per_device=10)
            await queue.submit(_payload("https://a.test", "fp-a"))
            await queue.submit(_payload("https://b.test", "fp-b"))
            with self.assertRaises(QueueFullError) as ctx:
                await queue.submit(_payload("https://c.test", "fp-c"))
            self.assertEqual(ctx.exception.scope, "global")
            # Rejected submissions must not leave phantom tasks behind.
            self.assertEqual(len(queue._tasks), 2)

        asyncio.run(scenario())

    def test_per_device_pending_cap_rejects_same_identity(self):
        async def scenario():
            queue = DistillTaskQueue(worker_count=1, max_pending=10, max_pending_per_device=2)
            await queue.submit(_payload("https://a.test", "fp-a"))
            await queue.submit(_payload("https://b.test", "fp-a"))
            with self.assertRaises(QueueFullError) as ctx:
                await queue.submit(_payload("https://c.test", "fp-a"))
            self.assertEqual(ctx.exception.scope, "device")
            # A different device is unaffected by the first device's backlog.
            result = await queue.submit(_payload("https://d.test", "fp-b"))
            self.assertEqual(result["status"], "pending")

        asyncio.run(scenario())

    def test_running_tasks_do_not_count_toward_pending(self):
        async def scenario():
            queue = DistillTaskQueue(worker_count=1, max_pending=1, max_pending_per_device=1)
            first = await queue.submit(_payload("https://a.test", "fp-a"))
            queue._tasks[first["task_id"]]["status"] = "running"
            second = await queue.submit(_payload("https://b.test", "fp-a"))
            self.assertEqual(second["status"], "pending")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()