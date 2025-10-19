import json, subprocess, sys, os

def run_factory(input_data):
    proc = subprocess.Popen(
        [sys.executable, os.path.join(os.path.dirname(__file__), '..', 'factory', 'main.py')],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate(json.dumps(input_data).encode())
    if err:
        print(err.decode(), file=sys.stderr)
    return json.loads(out.decode())

def test_sample_case():
    input_data = {
        "machines": {
            "assembler_1": {"crafts_per_min": 30},
            "chemical": {"crafts_per_min": 60}
        },
        "recipes": {
            "iron_plate": {
                "machine": "chemical",
                "time_s": 3.2,
                "in": {"iron_ore": 1},
                "out": {"iron_plate": 1}
            },
            "copper_plate": {
                "machine": "chemical",
                "time_s": 3.2,
                "in": {"copper_ore": 1},
                "out": {"copper_plate": 1}
            },
            "green_circuit": {
                "machine": "assembler_1",
                "time_s": 0.5,
                "in": {"iron_plate": 1, "copper_plate": 3},
                "out": {"green_circuit": 1}
            }
        },
        "modules": {
            "assembler_1": {"prod": 0.1, "speed": 0.15},
            "chemical": {"prod": 0.2, "speed": 0.1}
        },
        "limits": {
            "raw_supply_per_min": {"iron_ore": 5000, "copper_ore": 5000},
            "max_machines": {"assembler_1": 300, "chemical": 300}
        },
        "target": {"item": "green_circuit", "rate_per_min": 1800}
    }

    result = run_factory(input_data)
    assert result["status"] == "ok"
    assert abs(result["per_recipe_crafts_per_min"]["green_circuit"] - 1800) < 1e-6
    assert "assembler_1" in result["per_machine_counts"]
    assert "chemical" in result["per_machine_counts"]
    print("Sample case passed. Result:", json.dumps(result, indent=2))
