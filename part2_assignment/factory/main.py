import sys, json
import numpy as np
from scipy.optimize import linprog

def main():
    data = json.load(sys.stdin)

    machines = data["machines"]
    recipes = data["recipes"]
    modules = data.get("modules", {})
    limits = data.get("limits", {})
    target = data["target"]

    raw_caps = limits.get("raw_supply_per_min", {})
    machine_caps = limits.get("max_machines", {})

    target_item = target["item"]
    target_rate = target["rate_per_min"]

    recipe_names = sorted(recipes.keys())
    R = len(recipe_names)

    # Collect all items
    items = set()
    for rdata in recipes.values():
        items.update(rdata.get("in", {}).keys())
        items.update(rdata.get("out", {}).keys())
    items.add(target_item)
    item_list = sorted(items)
    I = len(item_list)
    item_index = {it: i for i, it in enumerate(item_list)}

    # Build A matrix and b vector for conservation
    A = np.zeros((I, R))

    for j, rname in enumerate(recipe_names):
        r = recipes[rname]
        mtype = r["machine"]
        base_speed = machines[mtype]["crafts_per_min"]
        speed_mod = modules.get(mtype, {}).get("speed", 0)
        prod_mod = modules.get(mtype, {}).get("prod", 0)

        time_s = r["time_s"]
        eff_crafts_per_min = base_speed * (1 + speed_mod) * 60 / time_s

        # Each craft: inflows negative, outflows positive (with productivity)
        for itm, amt in r.get("in", {}).items():
            A[item_index[itm], j] -= amt
        for itm, amt in r.get("out", {}).items():
            A[item_index[itm], j] += amt * (1 + prod_mod)

    b = np.zeros(I)
    for i, itm in enumerate(item_list):
        if itm == target_item:
            b[i] = target_rate
        elif itm in raw_caps:
            b[i] = 0  # we will constrain separately
        else:
            b[i] = 0

    # For raw materials: consumption <= cap
    # => -sum_r A[i,r]*x_r <= cap (since A[i,r] is -ve for input)

    # Machine usage constraints
    M = len(machine_caps)
    machine_types = sorted(machine_caps.keys())
    machine_index = {m: i for i, m in enumerate(machine_types)}

    usage_matrix = np.zeros((M, R))
    for j, rname in enumerate(recipe_names):
        r = recipes[rname]
        mtype = r["machine"]
        base_speed = machines[mtype]["crafts_per_min"]
        speed_mod = modules.get(mtype, {}).get("speed", 0)
        time_s = r["time_s"]
        eff_crafts_per_min = base_speed * (1 + speed_mod) * 60 / time_s
        usage_matrix[machine_index[mtype], j] = 1 / eff_crafts_per_min

    # Build LP
    # Objective: minimize total machines used
    c = np.zeros(R)
    for j, rname in enumerate(recipe_names):
        r = recipes[rname]
        mtype = r["machine"]
        base_speed = machines[mtype]["crafts_per_min"]
        speed_mod = modules.get(mtype, {}).get("speed", 0)
        time_s = r["time_s"]
        eff_crafts_per_min = base_speed * (1 + speed_mod) * 60 / time_s
        c[j] = 1 / eff_crafts_per_min

    A_eq = []
    b_eq = []

    for i, itm in enumerate(item_list):
        if itm == target_item or itm not in raw_caps:
            A_eq.append(A[i, :])
            b_eq.append(b[i])

    A_eq = np.array(A_eq)
    b_eq = np.array(b_eq)

    A_ub = []
    b_ub = []

    # raw caps
    for itm, cap in raw_caps.items():
        i = item_index[itm]
        A_ub.append(-A[i, :])
        b_ub.append(cap)

    # machine caps
    for mtype, cap in machine_caps.items():
        A_ub.append(usage_matrix[machine_index[mtype], :])
        b_ub.append(cap)

    A_ub = np.array(A_ub)
    b_ub = np.array(b_ub)

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=(0, None), method="highs")

    if res.success:
        x = res.x
        per_recipe = {r: float(x[j]) for j, r in enumerate(recipe_names)}

        # Compute per-machine counts
        per_machine = {m: 0.0 for m in machine_caps.keys()}
        for j, rname in enumerate(recipe_names):
            r = recipes[rname]
            mtype = r["machine"]
            base_speed = machines[mtype]["crafts_per_min"]
            speed_mod = modules.get(mtype, {}).get("speed", 0)
            time_s = r["time_s"]
            eff_crafts_per_min = base_speed * (1 + speed_mod) * 60 / time_s
            per_machine[mtype] += x[j] / eff_crafts_per_min

        raw_use = {}
        for itm, cap in raw_caps.items():
            i = item_index[itm]
            cons = -A[i, :] @ x
            raw_use[itm] = float(cons)

        out = {
            "status": "ok",
            "per_recipe_crafts_per_min": per_recipe,
            "per_machine_counts": {m: float(per_machine[m]) for m in per_machine},
            "raw_consumption_per_min": raw_use,
        }
    else:
        out = {
            "status": "infeasible",
            "max_feasible_target_per_min": 0.0,
            "bottleneck_hint": ["machine or raw limit"]
        }

    json.dump(out, sys.stdout, indent=2)

if __name__ == "__main__":
    main()
