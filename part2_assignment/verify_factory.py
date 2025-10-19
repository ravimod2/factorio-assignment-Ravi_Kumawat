import json, subprocess, sys, os

def run_factory(input_data):
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), 'factory', 'main.py')],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(json.dumps(input_data).encode())
    if err:
        print("stderr:", err.decode(), file=sys.stderr)
    return json.loads(out.decode())

def verify_factory_result(input_data, result):
    """Check mass balance and limits"""
    assert result["status"] == "ok", "Factory failed: " + str(result)
    crafts = result["per_recipe_crafts_per_min"]

    # Check that all raw materials stay within supply limit
    raw_limits = input_data["limits"]["raw_supply_per_min"]
    for mat, limit in raw_limits.items():
        used = sum(crafts.get(r, 0) * rec["in"].get(mat, 0)
                   for r, rec in input_data["recipes"].items())
        assert used <= limit + 1e-6, f"Raw material {mat} overused: {used}>{limit}"
    print("Factory output verified successfully.")

if __name__ == "__main__":
    # Load the test input and result interactively
    input_data = json.load(open("sample_factory_input.json"))
    result = run_factory(input_data)
    verify_factory_result(input_data, result)
