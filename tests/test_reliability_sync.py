import multiprocessing
import time

from cohezion.reliability.sync import AgentWorkspace, FileLock, SafeWriter


def test_file_lock_basic(tmp_path):
    lock_file = tmp_path / "test.lock"
    lock = FileLock(lock_file)

    with lock.acquire():
        assert lock_file.exists()
        # Nested acquisition should fail if it were NB, but we use LOCK_EX
        # flock is reentrant for the same process? Actually POSIX flock is not necessarily.
        # But for the same FD it might be. Let's test cross-process.
        pass


def _worker_lock_task(lock_path, shared_val):
    lock = FileLock(lock_path)
    with lock.acquire():
        curr = shared_val.value
        time.sleep(0.1)
        shared_val.value = curr + 1


def test_file_lock_concurrency(tmp_path):
    lock_file = tmp_path / "test.lock"
    manager = multiprocessing.Manager()
    shared_val = manager.Value("i", 0)

    processes = [multiprocessing.Process(target=_worker_lock_task, args=(lock_file, shared_val)) for _ in range(5)]

    for p in processes:
        p.start()
    for p in processes:
        p.join()

    assert shared_val.value == 5


def test_safe_writer_basic(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("initial")

    writer = SafeWriter(target)
    with writer.open() as f:
        f.write("updated")

    assert target.read_text() == "updated"


def test_safe_writer_failure(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("initial")

    writer = SafeWriter(target)
    try:
        with writer.open() as f:
            f.write("corrupted")
            raise RuntimeError("failure")
    except RuntimeError:
        pass

    assert target.read_text() == "initial"
    # Check that temp file is cleaned up
    temp_files = list(tmp_path.glob(".tmp_*"))
    assert len(temp_files) == 0


def test_agent_workspace_basic(tmp_path):
    base_dir = tmp_path / "src"
    base_dir.mkdir()
    f1 = base_dir / "file1.py"
    f1.write_text("print('hello')")

    workspace = AgentWorkspace(base_dir, [f1], workspace_root=tmp_path / "sandbox")

    with workspace.session() as staging:
        staged_f1 = staging / "file1.py"
        assert staged_f1.exists()
        assert staged_f1.read_text() == "print('hello')"

        # Modify in staging
        staged_f1.write_text("print('world')")

        # Base file should still be original
        assert f1.read_text() == "print('hello')"

        workspace.commit()

    # After commit and session end
    assert f1.read_text() == "print('world')"
    assert not (tmp_path / "sandbox").exists() or len(list((tmp_path / "sandbox").glob("*"))) == 0
