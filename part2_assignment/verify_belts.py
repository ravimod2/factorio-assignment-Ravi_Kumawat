import json, subprocess, sys, os

def run_belts(input_data):
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'belts', 'main.py')],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(json.dumps(input_data).encode())
    if err:
        print("stderr:", err.decode(), file=sys.stderr)
    return json.loads(out.decode())

def verify_belts_result(input_data, result):
    assert result["status"] == "ok", "Belt flow infeasible!"
    flows = result["flows"]
    nodes = input_data["nodes"]

    # Check flow conservation
    for node in nodes:
        inflow = sum(v for e, v in flows.items() if e.split("->")[1] == node)
        outflow = sum(v for e, v in flows.items() if e.split("->")[0] == node)
        net = inflow - outflow
        supply = input_data.get("supplies", {}).get(node, 0)
        demand = input_data.get("demands", {}).get(node, 0)
        assert abs(net + demand - supply) < 1e-6, f"Flow mismatch at {node}"
    print("Belt network verified successfully.")

if __name__ == "__main__":
    input_data = json.load(open("sample_belt_input.json"))
    result = run_belts(input_data)
    verify_belts_result(input_data, result)
