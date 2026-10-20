"""The review lock between processes, not only between threads.

review_lock pairs a process-wide RLock with an OS file lock (msvcrt on Windows,
flock on POSIX). The thread tests elsewhere only ever meet the RLock, so the
file lock, which is what keeps a CLI ingest and the running editor apart, needs
a second process to be contended at all.

Coordination runs over sentinel files, never over sleeps: the child announces
that it holds the lock, waits for the parent's release signal, writes a marker
and only then unlocks. The parent's acquisition must therefore see the marker.
Every wait is bounded, and the child holds the lock well under the roughly ten
seconds msvcrt.LK_LOCK retries before it gives up.
"""

import subprocess
import sys
import threading
import time

from io_paths import PIPELINE_DIR, review_lock

CHILD = """
import sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from io_paths import review_lock

register, held, release, releasing = (Path(a) for a in sys.argv[2:6])
with review_lock(register):
    held.write_text("held")
    deadline = time.monotonic() + 20
    while not release.exists():
        if time.monotonic() > deadline:
            sys.exit("release signal never came")
        time.sleep(0.01)
    releasing.write_text("releasing")
"""

WAIT = 15.0


def _wait_for(condition, timeout: float = WAIT) -> bool:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


# Guards the defect this test found: review_lock used to read a byte before
# locking, which raises PermissionError on Windows while another process holds it.
def test_a_second_process_waits_until_the_holder_releases(tmp_path) -> None:
    register = tmp_path / "pages"
    held, release, releasing = (
        tmp_path / name for name in ("held", "release", "releasing")
    )
    child = subprocess.Popen(
        [
            sys.executable,
            "-c",
            CHILD,
            str(PIPELINE_DIR),
            *map(str, (register, held, release, releasing)),
        ],
        stderr=subprocess.PIPE,
        text=True,
    )
    done = threading.Event()
    # What the contending thread saw: whether the holder had already announced
    # its release when the lock was granted, or the exception that ended it.
    outcome: list[object] = []

    def contender() -> None:
        try:
            with review_lock(register):
                outcome.append(releasing.exists())
        except Exception as exc:
            outcome.append(exc)
        finally:
            done.set()

    try:
        assert _wait_for(lambda: held.exists() or child.poll() is not None)
        assert held.exists(), f"child never took the lock: {child.stderr.read()}"
        thread = threading.Thread(target=contender, daemon=True)
        thread.start()
        # A negative check needs some window; the ordering assertion below is
        # what proves the wait, this only fails fast on a lock that never blocks.
        assert not done.wait(0.5), f"contender finished while held: {outcome}"
        release.write_text("go")
        assert done.wait(WAIT), "lock never acquired after the holder released"
        thread.join(WAIT)
        assert outcome == [True]
        assert child.wait(WAIT) == 0, child.stderr.read()
    finally:
        release.touch()
        if child.poll() is None:
            child.kill()
        child.wait(WAIT)
        child.stderr.close()
