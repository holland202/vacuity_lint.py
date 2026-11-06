# Repeatability probe

Experimental, unreleased companion script. Python 3.10+ on POSIX systems.
Run from a checkout; this script is not part of the installed `vacuity-lint`
console command. Linux is covered by the automated regression tests; other
POSIX platforms, including Android/Termux, have not been verified here.

The static scanner cannot tell whether a check's verdict changes across
executions. `repeatability_probe.py` runs an explicit command repeatedly,
records each exit code and output fingerprint, and keeps an earlier failure
visible even when a later execution succeeds.

## Run it

```sh
python3 repeatability_probe.py --selftest
python3 repeatability_probe.py --runs 10 --timeout 30 -- python3 verify_checks.py
python3 repeatability_probe.py --runs 10 --format json -- python3 verify_checks.py > repeatability.json
python3 repeatability_probe.py --runs 5 --cwd ./your-project -- python3 -m unittest discover -s tests
```

Options for the probe precede `--`; the remaining arguments are the exact
target command. No shell is inserted. To invoke a shell, pass it explicitly
as the command. Stdin is closed (`DEVNULL`); commands must be noninteractive.
At least two runs and a finite, positive per-execution timeout are required.

The command really executes, using the inherited environment and its normal
filesystem and network access. The probe does not edit source, reset state,
change random seeds, retry until success, or sandbox the command. Each run
uses the same working directory. Stateful checks can therefore change their
own inputs; that is useful evidence about repeatability, but it does not
identify the cause of a changed result.

## Outcomes

| JSON status | Meaning | Probe exit |
|---|---|---:|
| `consistent_pass` | All requested executions completed with exit 0 | 0 |
| `consistent_fail` | All completed with the same nonzero exit code | 1 |
| `inconsistent` | All completed, with at least two distinct exit codes | 1 |
| `incomplete` | Timeout, interruption, launch, capture or cleanup error; remaining runs were not attempted | 2 |

An incomplete measurement takes precedence even when the earlier completed
runs already disagree. All earlier attempts remain in the report. A killed
timed-out process has a recorded `process_returncode`, but its `exit_code`
is null: forced termination is not a completed verdict.

`output_varies` is separate from the exit-code outcome. For example, three
exit-0 runs printing different timestamps remain `consistent_pass` with
`output_varies: true`. Identical output cannot hide changing exit codes.
Different nonzero codes also count as inconsistent. Negative target exit
codes retain their POSIX signal meaning.

**A consistent finite sample does not establish determinism.** The tool
does not estimate a flakiness probability or issue a statistical confidence
claim. A changing result does not by itself demonstrate a source-code defect.
No actual project repeatability campaign is claimed by the fixture tests.

## Evidence

JSON schema version 1 includes:

- Exact command argv, absolute working directory, requested/completed counts,
  timeout, UTC start/finish times, Python interpreter/version, platform, and
  SHA-256 of the probe's source file when the measurement starts.
- Every attempt's index, kind, elapsed time, completed exit code or null,
  underlying process return code, and any execution error.
- Separate stdout/stderr byte counts and SHA-256 digests. Each contains a
  UTF-8 preview of at most the first 4096 raw bytes; invalid preview bytes
  are replaced for display. `preview_truncated` labels omitted bytes. Hashes
  use captured bytes before decoding, including output beyond the preview.
- Observed completed exit codes, output-signature count, and `output_varies`
  (`null` if no execution completed). Output summaries describe only
  completed executions; partial output remains on its incomplete attempt.

The console prints a summary. JSON carries the full observation record.
Argparse usage errors are written to stderr with exit 2, rather than a
measurement report. `--selftest` emits its six-control text report.

Output is spooled to temporary files and hashed in chunks, bounding capture
memory rather than command output size. Temporary disk usage is not capped.
The command timeout covers waiting for the top-level process, not operating
system process creation or subsequent capture hashing.

Each attempt starts a new POSIX session. On completion, timeout or handled
interruption, the probe sends SIGKILL to that process group and waits for the
top-level process, so background children in the same group are stopped.
Children that create a new session can escape this cleanup. This is not
process containment; background jobs and daemon commands are unsuitable.
Output fingerprints describe the captured snapshot when the attempt ends,
not an independently observed history of all descendant effects. Files,
dependencies and environment are not frozen or hashed by the probe.

## Controls and prior art

The six built-in deterministic controls force consistent pass, consistent
failure, alternating verdicts with identical output, changing output with
passing verdicts, timeout, and launch failure. Tests additionally check
binary output, truncation, partial evidence, errors, interruption, process
group cleanup and CLI behavior. A deliberately constant-pass classifier
must fail the self-test controls.

Repeated testing is established practice, not a novelty claim.
[pytest-repeat](https://github.com/pytest-dev/pytest-repeat) repeats pytest
tests; [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures)
reruns failing pytest tests. Prefer
those when their pytest integration fits. This small companion supplies an
argv-based command-level report without adding a pytest dependency. The
suite mutation probe already checks its baseline twice before mutation;
this script exposes a separate configurable repeated-command measurement.

Primary project documentation checked 2026-11-06. Tests and controls here
are AI-assisted engineering checks, not independent human validation.
