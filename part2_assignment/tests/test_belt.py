import json, subprocess, sys, os

def run_belts(input_data):
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), '..', 'belts', 'main.py')],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(json.dumps(input_data).encode())
    if err:
        print(err.decode(), file=sys.stderr)
    return json.loads(out.decode())

def test_sample_case():
    # Simple feasible case with two belts
    input_data = {
        "nodes": ["S", "A", "B", "T"],
        "edges": [
            {"from": "S", "to": "A", "lo": 0, "hi": 10},
            {"from": "A", "to": "B", "lo": 0, "hi": 5},
            {"from": "B", "to": "T", "lo": 0, "hi": 10},
            {"from": "A", "to": "T", "lo": 0, "hi": 3}
        ],
        "supplies": {"S": 10},
        "demands": {"T": 10},
        "node_caps": {"A": 8, "B": 10}
    }

    result = run_belts(input_data)
    assert result["status"] == "ok"
    flow = result["flows"]
    total_out = sum(f for e, f in flow.items() if e.startswith("S->"))
    assert abs(total_out - 10) < 1e-6, f"Expected 10 flow out of S, got {total_out}"
    print("Sample case passed. Result:", json.dumps(result, indent=2))
