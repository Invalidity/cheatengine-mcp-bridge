"""Issue #53: create inactive Auto Assembler records against a fake CE address list."""
from lua_harness import BRIDGE_LUA, arg_path, finish, load, run_lua

source = load(arg_path(1, BRIDGE_LUA))
begin = source.index("local UNIT18_TYPE_MAP = {")
end = source.index("function cmd_delete_memory_record(params)", begin)
stub = r'''
records = {}
function getAddressList()
  return { createMemoryRecord = function(self)
    local r = {ID = #records + 1, Active = true}
    function r:delete() self.deleted = true end
    records[#records + 1] = r
    return r
  end }
end
'''
checks = r'''
local aa = cmd_create_memory_record({description="script", type="vtAutoAssembler", script="\239\187\191[ENABLE]\n[DISABLE]"})
assert(aa.success and records[1].VarType == "vtAutoAssembler")
assert(records[1].Script == "[ENABLE]\n[DISABLE]" and records[1].Active == false)
assert(not cmd_create_memory_record({description="empty",type="autoassembler"}).success)
assert(not cmd_create_memory_record({description="missing",type="dword"}).success)
local val = cmd_create_memory_record({description="health",type="dword",address="game.exe+10"})
assert(val.success and records[2].Address == "game.exe+10" and records[2].VarType == "vtDword")
return "PASS: inactive table records and address validation"
'''
ok, result = run_lua(stub + source[begin:end] + checks)
print(result)
if not ok or not result.startswith("PASS"):
    raise SystemExit(1)
finish()
