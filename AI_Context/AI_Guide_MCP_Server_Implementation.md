# Agent Guide: Working with the Cheat Engine MCP Bridge

This guide is for AI agents using the bridge. It explains how the pieces fit together, the rules that keep the target
and the user's machine safe, and the habits that get good results. For every tool's parameters and results, see
`MCP_Bridge_Command_Reference.md` (also served as `cheatengine://docs/command-reference`).

---

## Rules that matter most

1. **A failed call may still have run.** If a call times out or the connection drops, its outcome is *unknown*. The
   server never retries. Check the state (read the memory, `list_breakpoints`, `list_jobs`) before repeating
   anything that writes.
2. **Addresses don't survive a restart.** After the target restarts, find addresses again with symbols, AOB
   signatures or pointer chains. Never reuse an old absolute address.
3. **Prefer hardware breakpoints.** `set_breakpoint` and `set_data_breakpoint` use the CPU's debug registers
   (DR0–DR3), which don't change the target's code. Software breakpoints (`0xCC`) are easier to detect.
4. **Clean up.** Remove breakpoints and stop DBVM watches when you're done (`remove_breakpoint`,
   `clear_all_breakpoints`, `stop_dbvm_watch`).
5. **Respect the profile.** If a tool is missing or refused, the user's profile hides it. `policy_info` shows what is
   allowed. Ask the user rather than looking for a way around it.

The user should also have turned off **Settings → Extra → "Query memory region routines"** in Cheat Engine. With it
on, scanning protected pages can crash Windows (`CLOCK_WATCHDOG_TIMEOUT`).

---

## How it fits together

```
AI agent
   │  MCP (JSON-RPC over stdio)
   ▼
mcp_cheatengine.py ─ Python MCP server (SDK 2.x)
   │  length-prefixed JSON over \\.\pipe\CE_MCP_Bridge_v99
   ▼
ce_mcp_bridge.lua ─ inside Cheat Engine
   ├─ worker thread: waits on the pipe, so Cheat Engine's window never freezes
   └─ main thread: runs every Cheat Engine API call
   │
   ▼
Target process
```

- **One client at a time.** The pipe has a single connection. A second MCP client or test script gets error 231
  ("All pipe instances are busy").
- **One call at a time.** The server sends calls in order, never in parallel.
- **32-bit and 64-bit targets both work.** The bridge checks the target's architecture and uses the right pointer
  size and register names. `get_process_info` tells you which one you have.

---

## A good way to start

1. `ping`: is the bridge loaded? (`process_id: 0` means nothing is attached yet.)
2. `get_process_info`: which process, and is it 32-bit or 64-bit?
3. `open_process` if the user wants a different target.
4. `enum_modules`: where the main module and DLLs are loaded.

---

## Tools by task

### Finding values

| Tool | Use it to |
|---|---|
| `scan_all`, `next_scan`, `get_scan_results` | Find a value, then narrow the results after it changes |
| `aob_scan`, `aob_scan_module_unique` | Find a byte pattern, such as `48 8B 05 ?? ?? ?? ??` |
| `search_string` | Find text in memory |
| `generate_signature` | Make a unique AOB pattern for an address, so it can be found again after an update |
| `start_job` with `scan_all`, `aob_scan`, ... | Run a long scan in the background; then `wait_for_job` and `get_job_result` |

Use `start_job` for anything that might take more than a few seconds. A blocking call can hit the timeout even
though Cheat Engine is still working on it.

### Reading memory

| Tool | Use it to |
|---|---|
| `read_memory`, `read_integer`, `read_string` | Read bytes, numbers (byte to qword, float, double) or text |
| `read_pointer_chain` | Follow a path like `[[base+0x10]+0x20]+0x8` in one call |
| `read_struct` | Read many typed fields from one block in one call |
| `snapshot_region`, `diff_snapshots` | Compare a region before and after something happens |

### Understanding code and objects

| Tool | Use it to |
|---|---|
| `disassemble`, `get_instruction_info` | Read instructions at an address |
| `find_function_boundaries`, `analyze_function` | Find where a function starts and ends, and what it calls |
| `find_xrefs`, `find_references`, `find_call_references` | Find code that uses an address or calls a function |
| `find_string_refs` | Find code that uses a given string |
| `get_rtti_classname`, `recover_struct` | Name a C++ object and guess its fields |
| `pe_info`, `pe_imports`, `pe_exports` | Read a module's headers, imports and exports |

### Pointers that survive restarts

1. `find_pointer_path` with `save_as` finds chains to a value and saves them as a set.
2. After the target restarts, find the same value again (scan or signature).
3. `compare_pointer_paths` keeps only the chains that still lead to it. Repeat a few times for stable results.

### Watching what touches a value

| Tool | Use it to |
|---|---|
| `set_data_breakpoint` | Catch the instruction that reads or writes an address |
| `set_breakpoint` | Catch execution of an instruction; record registers and the stack |
| `get_breakpoint_hits` | Collect what was recorded |
| `start_dbvm_watch`, `poll_dbvm_watch` | Trace access below the operating system (needs DBVM) |

Up to four hardware breakpoints can be active at once.

### Changing things (needs the `patch` or `full` profile)

`write_integer`, `write_memory`, `write_string`, `auto_assemble`, `allocate_memory` and friends change the target.
Confirm with the user before writing to a process they care about, and read the value back afterwards.

---

## Checking your work

- Read back anything you write.
- After a restart, re-resolve addresses before using them.
- Report what you actually saw. A tool's `success: true` means the command ran, not that the game behaves the way
  you expect.

The bridge's own logic is covered by offline tests (`python tests/run_all.py`); live behavior is checked with
`MCP_Server/test_mcp.py` and `tests/live_smoke.py` against a running Cheat Engine.
