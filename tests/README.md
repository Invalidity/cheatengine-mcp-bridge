# Tests

Most tests here run **without Cheat Engine**. They run the real bridge code against a fake Cheat Engine, so they are
quick (about a minute) and safe to run after every change.

```bash
python tests/run_all.py              # all suites
python tests/run_all.py -v           # also show each suite's full output
python tests/run_all.py --real       # also check PE and RTTI parsing against real Windows DLLs
python tests/run_all.py --mutation   # also check that the suites catch deliberate bugs
python tests/run_all.py --strict     # treat skipped suites as failures
python tests/test_lua_jobs.py        # run one suite (exit code 0 means everything passed)
```

## What you need

- Windows and `pip install -r MCP_Server/requirements.txt`.
- Cheat Engine's `lua53-64.dll`. The tests look in the usual install folders, or you can point `CE_LUA_DLL` at it.
  The bridge is written for Cheat Engine's Lua 5.3, so the tests use that exact engine. Without it, the Lua suites
  are skipped, not failed. (This is what happens in GitHub Actions.)

## The suites

### Lua bridge (run inside Cheat Engine's Lua engine)

| File | What it checks |
|---|---|
| `test_lua_robustness.py` | The JSON encoder and decoder (escapes, 64-bit numbers, bad UTF-8), that a command never crashes the dispatcher, and that breakpoint callbacks always let the target continue |
| `test_lua_jobs.py` | `read_memory` formats, `read_struct`, `batch`, `bridge_status`, and background jobs: starting, polling, cancelling, limits and cleanup |
| `test_lua_analysis.py` | PE imports, exports and TLS callbacks, address conversion, RTTI, string references, code caves, pointer paths, snapshots and name import/export, on made-up 64-bit **and** 32-bit images |
| `test_lua_xrefs.py` | `find_xrefs`: calls and jumps, RIP-relative operands (and whether they read or write), absolute pointers, RVAs, address ranges and limits |
| `test_lua_pathsets.py` | Saving pointer paths and comparing them across simulated restarts: which chains survive, near misses with corrected offsets, missing modules, paging and size limits |
| `test_lua_load.py` | Loads the **whole** bridge file in a fake Cheat Engine. Loading it twice must stop the first copy, and every command must give a proper reply. This catches problems that testing single functions misses |
| `test_lua_handle.py`, `test_lua_float.py`, `test_lua_table_records.py` | Regression tests for window handles, float/double writes and Auto Assembler table records |

### Python server

| File | What it checks |
|---|---|
| `test_client_retry.py` | The client against a fake bridge on a real named pipe: no command runs twice, reconnecting, timeouts that don't hang, bad UTF-8, error replies |
| `test_client_concurrency.py` | Calls from several threads never mix up their replies |
| `test_client_jobs.py` | Job and batch tools pass their parameters through correctly; `wait_for_job` behaves |
| `test_client_analysis.py` | Analysis tools clean their parameters, wrap jobs correctly and register the right schemas |
| `test_policy.py` | Safety profiles: every tool is classified, profiles nest, allow/deny lists work, nothing slips through `batch` or `start_job`, and the tool labels (read-only, destructive, ...) match the profile tiers. It also starts the real server with different settings, sending only calls that must be refused |

### Extra checks with `--real`

- `test_lua_analysis.py --real` parses `user32.dll` and `msvcp140.dll` as Windows loaded them and compares the result
  with Windows itself: exports and imports against `GetProcAddress`, section flags against `VirtualQuery`, and the
  RTTI scan against known `std::` exception classes.
- `test_lua_xrefs.py --real` compares `find_xrefs` with an independent disassembler, [capstone](https://www.capstone-engine.org/)
  (`pip install capstone`). Both must find exactly the same instructions. Without capstone this part is skipped.

The fake Cheat Engine API shared by these suites is in `fake_ce.py`.

## Live smoke test (needs Cheat Engine)

```bash
python tests/live_smoke.py [--only SECTION] [-v]
```

This checks what only a real Cheat Engine can confirm. It starts its own throwaway target (`live_target.py`),
attaches Cheat Engine to it, runs about 60 checks through the real MCP tools, and then re-attaches whatever Cheat
Engine had open before.

Sections: connection, attach, memory, scan jobs, PE analysis, cross-references, snapshots, breakpoints and bridge
health. It exits with code 77 (skipped) when the bridge isn't running. It isn't part of `run_all.py`.

**What it found the first time** (all fixed, and now covered offline too):

- Many newer tools answered just `true`, because three helper functions with the same name overwrote each other.
- Running the script a second time left the old bridge serving the pipe next to the new one.
- "Break" mode didn't stop the thread. A breakpoint callback has to return a non-zero number to keep the thread
  stopped; `nil`, `false`, `true` and `0` all let it continue.

**Cheat Engine quirks worth knowing:**

- In Cheat Engine 7.6, `debug_isBroken()` returns a function instead of `true` or `false`, so the bridge never
  relies on it.
- The debugger used for the first breakpoint comes from Cheat Engine's settings. The VEH debugger crashed the Python
  test target, so the smoke test picks the Windows debugger explicitly (`debug_process(1)`).

## Mutation check

`mutation_check.py` makes one small, realistic bug at a time in a copy of `ce_mcp_bridge.lua` and expects the matching
suite to fail. Passing tests only mean something if the tests *can* fail.

If you change the bridge and a mutant's anchor text no longer exists, it's reported as `STALE`; update its text in
`mutation_check.py`. One mutant is a known survivor: a defensive 32-bit check that can't change any visible result.

## Writing tests

- Suites print lines starting with `PASS` or `FAIL`. `testkit.finish()` counts them and sets the exit code. A run
  fails if anything failed, if nothing passed, or if a line contains `LUA ERROR` or `COMPILE FAIL`.
- Lua suites pull the real functions out of `ce_mcp_bridge.lua` (see `lua_harness.func_end` and `between`) and run
  them with fake Cheat Engine functions such as `createMemScan`, `readBytes` and `enumModules`.
- When you add a command, extend the matching suite **and** add a mutant for its most important branch.
- A passing fake test proves the bridge's logic, not that Cheat Engine behaves like the fake. Anything that depends
  on the real API (scan events, hardware breakpoints, DBVM) still needs `MCP_Server/test_mcp.py` or a manual check.
