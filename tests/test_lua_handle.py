"""Issue #69: accept CE's own hexadecimal window handles without changing the API."""
from lua_harness import BRIDGE_LUA, arg_path, finish, func_block, load, run_lua

source = load(arg_path(1, BRIDGE_LUA))
helper = func_block(source, "local function parseHandle(hexStr)")
ok, result = run_lua(helper + r'''
assert(parseHandle("0x00070E2C") == 0x70E2C)
assert(parseHandle(" 0X70e2c ") == 0x70E2C)
assert(parseHandle("70E2C") == 0x70E2C)
assert(parseHandle(0x70E2C) == 0x70E2C)
assert(parseHandle(-1) == nil)
assert(parseHandle(1.5) == nil)
assert(parseHandle({}) == nil)
assert(parseHandle("0x") == nil)
assert(parseHandle("bad!") == nil)
return "PASS: window handle parsing"
''')
print(result)
if not ok or not result.startswith("PASS"):
    raise SystemExit(1)
finish()
