import sys

import pytest


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_loading():
    try:
        pass
    except Exception:
        import pytest

        pytest.fail("Crashtracker failed to load")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_available():
    import ddtrace.internal.datadog.profiling.crashtracker as crashtracker

    assert crashtracker.is_available


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_config():
    import pytest

    from tests.internal.crashtracker.utils import read_files
    from tests.internal.crashtracker.utils import start_crashtracker

    start_crashtracker(1234)
    stdout_msg, stderr_msg = read_files(["stdout.log", "stderr.log"])
    if stdout_msg or stderr_msg:
        pytest.fail("contents of stdout.log: %s, stderr.log: %s" % (stdout_msg, stderr_msg))


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_config_bytes():
    import pytest

    import ddtrace.internal.datadog.profiling.crashtracker as crashtracker
    from tests.internal.crashtracker.utils import read_files

    try:
        crashtracker.set_url(b"http://localhost:1234")
        crashtracker.set_service(b"my_favorite_service")
        crashtracker.set_version(b"v0.0.0.0.0.0.1")
        crashtracker.set_runtime(b"4kph")
        crashtracker.set_runtime_version(b"v3.1.4.1")
        crashtracker.set_library_version(b"v2.7.1.8")
        crashtracker.set_stdout_filename(b"stdout.log")
        crashtracker.set_stderr_filename(b"stderr.log")
        crashtracker.set_alt_stack(False)
        crashtracker.set_resolve_frames_full()
        assert crashtracker.start()
    except Exception:
        pytest.fail("Exception when starting crashtracker")

    stdout_msg, stderr_msg = read_files(["stdout.log", "stderr.log"])
    if stdout_msg or stderr_msg:
        pytest.fail("contents of stdout.log: %s, stderr.log: %s" % (stdout_msg, stderr_msg))


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_simple():
    # This test does the following
    # 1. Finds a random port in the range 10000-20000 it can bind to (5 retries)
    # 2. Listens on that port for new connections
    # 3. Starts the crashtracker with the URL set to the port
    # 4. Crashes the process
    # 5. Verifies that the crashtracker sends a crash report to the server
    import ctypes
    import os

    import tests.internal.crashtracker.utils as utils

    # Part 1 and 2
    port, sock = utils.crashtracker_receiver_bind()
    assert port
    assert sock

    # Part 3 and 4, Fork, setup crashtracker, and crash
    pid = os.fork()
    if pid == 0:
        assert utils.start_crashtracker(port)
        stdout_msg, stderr_msg = utils.read_files(["stdout.log", "stderr.log"])
        assert not stdout_msg
        assert not stderr_msg

        ctypes.string_at(0)
        exit(-1)

    # Part 5
    # Check to see if the listening socket was triggered, if so accept the connection
    # then check to see if the resulting connection is readable
    conn = utils.listen_get_conn(sock)
    assert conn

    # The crash came from string_at.  Since the over-the-wire format is multipart, chunked HTTP,
    # just check for the presence of the raw string 'string_at' in the response.
    data = utils.conn_to_bytes(conn)
    conn.close()
    assert b"string_at" in data


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_simple_fork():
    # This is similar to the simple test, except crashtracker initialization is done
    # in the parent
    import ctypes
    import os

    import tests.internal.crashtracker.utils as utils

    # Part 1 and 2
    port, sock = utils.crashtracker_receiver_bind()
    assert port
    assert sock

    # Part 3, setup crashtracker in parent
    assert utils.start_crashtracker(port)
    stdout_msg, stderr_msg = utils.read_files(["stdout.log", "stderr.log"])
    assert not stdout_msg
    assert not stderr_msg

    # Part 4, Fork and crash
    pid = os.fork()
    if pid == 0:
        ctypes.string_at(0)
        exit(-1)  # just in case

    # Part 5, check
    conn = utils.listen_get_conn(sock)
    assert conn

    data = utils.conn_to_bytes(conn)
    conn.close()
    assert b"string_at" in data


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_simple_sigbus():
    # This is similar to the simple fork test, except instead of raising a SIGSEGV,
    # it organically raises a real SIGBUS.
    import ctypes
    from ctypes.util import find_library
    import os
    import tempfile

    import tests.internal.crashtracker.utils as utils

    # Part 0, set up the interface to mmap.  We don't want to use mmap.mmap because it has too much protection.
    libc = ctypes.CDLL(find_library("c"))
    assert libc
    libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_long]
    libc.mmap.restype = ctypes.c_void_p
    PROT_WRITE = ctypes.c_int(0x2)  # Maybe there's a better way to get this constant?
    MAP_PRIVATE = ctypes.c_int(0x02)

    # Part 1 and 2
    port, sock = utils.crashtracker_receiver_bind()
    assert port
    assert sock

    # Part 3, setup crashtracker in parent
    assert utils.start_crashtracker(port)
    stdout_msg, stderr_msg = utils.read_files(["stdout.log", "stderr.log"])
    assert not stdout_msg
    assert not stderr_msg

    # Part 4, Fork and crash
    pid = os.fork()
    if pid == 0:
        with tempfile.TemporaryFile() as tmp_file:
            tmp_file.write(b"aaaaaa")  # write some data to the file
            fd = tmp_file.fileno()  # get the file descriptor
            mm = libc.mmap(
                ctypes.c_void_p(0), ctypes.c_size_t(4096), PROT_WRITE, MAP_PRIVATE, ctypes.c_int(fd), ctypes.c_long(0)
            )
            assert mm
            assert mm != ctypes.c_void_p(-1).value
            arr_type = ctypes.POINTER(ctypes.c_char * 4096)
            arr = ctypes.cast(mm, arr_type).contents
            arr[4095] = b"x"  # sigbus
        exit(-1)  # just in case

    # Part 5, check
    conn = utils.listen_get_conn(sock)
    assert conn

    data = utils.conn_to_bytes(conn)
    conn.close()
    assert data


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_raise_sigsegv():
    import os
    import signal

    import tests.internal.crashtracker.utils as utils

    # Part 1 and 2
    port, sock = utils.crashtracker_receiver_bind()
    assert port
    assert sock

    assert utils.start_crashtracker(port)
    stdout_msg, stderr_msg = utils.read_files(["stdout.log", "stderr.log"])
    assert not stdout_msg
    assert not stderr_msg

    # Part 4, raise SIGSEGV
    pid = os.fork()
    if pid == 0:
        os.kill(os.getpid(), signal.SIGSEGV.value)
        exit(-1)

    # Part 5, check
    conn = utils.listen_get_conn(sock)
    assert conn

    data = utils.conn_to_bytes(conn)
    conn.close()
    assert b"os_kill" in data


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux only")
@pytest.mark.subprocess()
def test_crashtracker_raise_sigbus():
    import os
    import signal

    import tests.internal.crashtracker.utils as utils

    # Part 1 and 2
    port, sock = utils.crashtracker_receiver_bind()
    assert port
    assert sock

    assert utils.start_crashtracker(port)
    stdout_msg, stderr_msg = utils.read_files(["stdout.log", "stderr.log"])
    assert not stdout_msg
    assert not stderr_msg

    # Part 4, raise SIGBUS
    pid = os.fork()
    if pid == 0:
        os.kill(os.getpid(), signal.SIGBUS.value)
        exit(-1)

    # Part 5, check
    conn = utils.listen_get_conn(sock)
    assert conn

    data = utils.conn_to_bytes(conn)
    conn.close()
    assert b"os_kill" in data
