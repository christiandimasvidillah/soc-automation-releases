from __future__ import annotations

import multiprocessing as mp
import tempfile
import time
from pathlib import Path

from ticket_lock import TicketLockStore


def contend(database: str, owner: str, queue: mp.Queue) -> None:
    store = TicketLockStore(database, owner, lease_seconds=2)
    try:
        queue.put(store.acquire("SOC-100"))
        time.sleep(0.2)
    finally:
        store.close()


def main() -> None:
    mp.freeze_support()

    with tempfile.TemporaryDirectory(prefix="ticket-lock-") as td:
        database = str(Path(td) / "locks.sqlite3")
        owner_a = TicketLockStore(database, "owner-a", lease_seconds=1)
        owner_b = TicketLockStore(database, "owner-b", lease_seconds=1)

        assert owner_a.acquire("SOC-1") is True
        assert owner_b.acquire("SOC-1") is False
        assert owner_a.acquire("SOC-1") is True
        assert owner_a.renew_owned() == 1
        owner_a.release("SOC-1")
        assert owner_b.acquire("SOC-1") is True
        owner_b.release_all()

        assert owner_a.acquire("SOC-2") is True
        time.sleep(1.1)
        assert owner_b.acquire("SOC-2") is True
        owner_b.release_all()

        owner_a.close()
        owner_b.close()

        context = mp.get_context("spawn")
        queue = context.Queue()
        first = context.Process(target=contend, args=(database, "process-a", queue))
        second = context.Process(target=contend, args=(database, "process-b", queue))
        first.start()
        second.start()
        first.join(10)
        second.join(10)

        assert first.exitcode == 0, f"Process A exit code: {first.exitcode}"
        assert second.exitcode == 0, f"Process B exit code: {second.exitcode}"

        results = [queue.get(timeout=2), queue.get(timeout=2)]
        assert results.count(True) == 1
        assert results.count(False) == 1

        queue.close()
        queue.join_thread()

    print("Cross-process ticket lock tests: OK")


if __name__ == "__main__":
    main()
