"""Issue #41: float reads must not format fractional values as integers."""
from lua_harness import BRIDGE_LUA, arg_path, finish, func_block, load, run_lua

source = load(arg_path(1, BRIDGE_LUA))
parts = [func_block(source, "local function toHex(num)"),
         func_block(source, "function cmd_read_integer(params)")]
checks = r'''
function getAddressSafe(x) return tonumber(x) end
function readFloat(x) return 1.5 end
function readDouble(x) return -2.25 end
function readInteger(x) return 42 end
local f = cmd_read_integer({address=4096, type="float"})
assert(f.success and f.value == 1.5 and f.hex == "00 00 C0 3F")
local d = cmd_read_integer({address=4096, type="double"})
assert(d.success and d.value == -2.25 and d.hex == "00 00 00 00 00 00 02 C0")
local i = cmd_read_integer({address=4096, type="dword"})
assert(i.success and i.hex == "0x0000002A")
return "PASS: float and double values and byte encodings"
'''
ok, result = run_lua("\n".join(parts) + checks)
print(result)
if not ok or not result.startswith("PASS"):
    raise SystemExit(1)
finish()
