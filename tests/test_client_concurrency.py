"""The shared bridge transport serializes simultaneous MCP requests."""
import importlib.util
import json
import sys
import threading
import time

from testkit import BRIDGE_PY, finish

spec = importlib.util.spec_from_file_location("bridge_under_test", BRIDGE_PY)
mod = importlib.util.module_from_spec(spec)
old_stdout = sys.stdout
spec.loader.exec_module(mod)
sys.stdout = old_stdout


class FakeClient(mod.CEBridgeClient):
    def __init__(self):
        super().__init__()
        self.in_flight = 0
        self.max_in_flight = 0

    @property
    def connected(self):
        return True

    def _exchange_with_timeout(self, request, method):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        time.sleep(0.05)
        self.in_flight -= 1
        return {"id": json.loads(request)["id"], "result": {"success": True}}

    def close(self):
        pass


client = FakeClient()
results = []
threads = [threading.Thread(target=lambda: results.append(client.send_command("ping"))) for _ in range(8)]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join(timeout=5)
ok = len(results) == 8 and all(r["success"] for r in results) and client.max_in_flight == 1
print(("PASS" if ok else "FAIL") + " concurrent calls use one exchange at a time")
finish()
