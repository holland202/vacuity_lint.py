
# Written by suite_mutation_probe.py. Collects executed line numbers for ONE
# target file, in every Python process the suite starts, and appends them to
# a shared file. Imported automatically by CPython at interpreter startup
# because this directory is first on PYTHONPATH.
import atexit, os, sys
try:
    import threading
except Exception:
    threading = None

_TARGET = os.environ.get("SMP_COV_TARGET")
_OUT = os.environ.get("SMP_COV_OUT")
_seen = set()


def _tracer(frame, event, arg):
    if event == "line":
        try:
            if os.path.realpath(frame.f_code.co_filename) == _TARGET:
                _seen.add(frame.f_lineno)
        except Exception:
            pass
    return _tracer


def _flush():
    if not _seen:
        return
    try:
        with open(_OUT, "a") as fh:
            fh.write("".join("%d\n" % n for n in sorted(_seen)))
    except Exception:
        pass


def _log(kind, pid, detail=""):
    path = os.environ.get("SMP_ATTACH_LOG")
    if not path:
        return
    try:
        with open(path, "a") as fh:
            fh.write("%s %d %s\n" % (kind, pid, detail))
    except Exception:
        pass


def _looks_like_python(argv):
    try:
        head = argv[0] if isinstance(argv, (list, tuple)) else argv
        return "python" in os.path.basename(str(head)).lower()
    except Exception:
        return False


# Records every Python child this process starts.
# Deliberately DOES NOT re-inject the tracer into the child: re-injecting
# would change the behaviour of the suite under audit. This only observes.
# A Python child that starts and never attaches appears as a LAUNCH with no
# matching ATTACH, and reconciliation fails closed. That is the bounded
# guarantee -- attached, or the audit stops.
def _install_launch_recorder():
    try:
        import subprocess
    except Exception:
        return
    _real_popen_init = subprocess.Popen.__init__

    def _init(self, args, *a, **kw):
        _real_popen_init(self, args, *a, **kw)
        try:
            if _looks_like_python(args):
                _log("LAUNCH", self.pid, str(args)[:200])
        except Exception:
            pass

    subprocess.Popen.__init__ = _init

    for name in ("execv", "execve", "execvp", "execvpe"):
        real = getattr(os, name, None)
        if real is None:
            continue

        def _mk(real_fn):
            def _wrapped(path, args, *rest):
                try:
                    if _looks_like_python([path]):
                        _log("LAUNCH", os.getpid(), str(path)[:200])
                except Exception:
                    pass
                return real_fn(path, args, *rest)
            return _wrapped

        try:
            setattr(os, name, _mk(real))
        except Exception:
            pass


if _TARGET and _OUT:
    _log("ATTACH", os.getpid(), sys.executable)
    _install_launch_recorder()
    atexit.register(_flush)
    sys.settrace(_tracer)
    if threading is not None:
        threading.settrace(_tracer)
