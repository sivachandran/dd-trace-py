from ..types import StringType

def set_url(url: StringType) -> None: ...
def set_service(service: StringType) -> None: ...
def set_env(env: StringType) -> None: ...
def set_version(version: StringType) -> None: ...
def set_runtime(runtime: StringType) -> None: ...
def set_runtime_version(runtime_version: StringType) -> None: ...
def set_library_version(profiler_version: StringType) -> None: ...
def set_stdout_filename(filename: StringType) -> None: ...
def set_stderr_filename(filename: StringType) -> None: ...
def set_alt_stack(alt_stack: bool) -> None: ...
def set_resolve_frames_disable() -> None: ...
def set_resolve_frames_fast() -> None: ...
def set_resolve_frames_full() -> None: ...
def set_profiling_state_sampling(on: bool) -> None: ...
def set_profiling_state_unwinding(on: bool) -> None: ...
def set_profiling_state_serializing(on: bool) -> None: ...
def start() -> bool: ...
