import json

def gen_case():
    data = {
        "nodes": ["S", "A", "B", "T"],
        "edges": [
            {"from": "S", "to": "A", "lo": 0, "hi": 10},
            {"from": "A", "to": "B", "lo": 0, "hi": 5},
            {"from": "B", "to": "T", "lo": 0, "hi": 10}
        ],
        "supplies": {"S": 10},
        "demands": {"T": 10},
        "node_caps": {"A": 8, "B": 10}
    }
    with open("sample_belt_input.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Generated sample_belt_input.json")

if __name__ == "__main__":
    gen_case()
