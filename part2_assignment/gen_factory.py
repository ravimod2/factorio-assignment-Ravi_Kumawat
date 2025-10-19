import json, random

def gen_case(seed=0):
    random.seed(seed)
    return {
        "machines": {
            "m1": {"crafts_per_min": 30},
            "m2": {"crafts_per_min": 50}
        },
        "recipes": {
            "a": {"machine": "m1", "time_s": 2, "in": {"ore": 1}, "out": {"a": 1}},
            "b": {"machine": "m2", "time_s": 3, "in": {"a": 2}, "out": {"b": 1}},
        },
        "modules": {"m1": {"prod": 0.1, "speed": 0.1}, "m2": {"prod": 0.2, "speed": 0.05}},
        "limits": {
            "raw_supply_per_min": {"ore": 200},
            "max_machines": {"m1": 10, "m2": 10}
        },
        "target": {"item": "b", "rate_per_min": 50}
    }

if __name__ == "__main__":
    case = gen_case()
    with open("sample_factory_input.json", "w") as f:
        json.dump(case, f, indent=2)
    print("Generated sample_factory_input.json")
