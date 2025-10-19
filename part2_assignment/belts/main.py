#!/usr/bin/env python3
"""
belts/main.py

Reads JSON from stdin and writes JSON to stdout. Solves the "Belts with Bounds and Node Caps" problem.

Input JSON format expected (flexible but fields must exist):
{
  "edges": [ {"from":"a","to":"b","lo":0,"hi":100}, ... ],
  "sources": {"s1":900, "s2":600, ...},
  "sink": "sink",
  "node_caps": {"a":200, "b":500, ...}   # optional
}

Output (success):
{
  "status": "ok",
  "max_flow_per_min": 1500,
  "flows": [ {"from":"s1","to":"a","flow":900}, ... ]
}

Output (infeasible):
{
  "status": "infeasible",
  "cut_reachable": [...],
  "deficit": {"demand_balance": 300, "tight_nodes": [...], "tight_edges": [ {"from":...,"to":...,"flow_needed":300} ] }
}

This implementation uses a deterministic Dinic max-flow (neighbors visited in insertion / sorted order)
and follows the lower-bound -> circulation -> supply->sink procedure described in the assignment.

No extra prints.
"""

import sys
import json
from collections import deque, defaultdict

EPS = 1e-9

# --------------------- Deterministic Dinic ---------------------
class Edge:
    __slots__ = ('to','rev','cap','orig')
    def __init__(self, to, rev, cap):
        self.to = to
        self.rev = rev
        self.cap = float(cap)
        self.orig = float(cap)

class Dinic:
    def __init__(self, n):
        self.n = n
        self.g = [[] for _ in range(n)]
    def add_edge(self, u, v, c):
        # deterministic insertion order
        ulist = self.g[u]
        vlist = self.g[v]
        ulist.append(Edge(v, len(vlist), c))
        vlist.append(Edge(u, len(ulist)-1, 0.0))
        # return reference to forward edge for bookkeeping
        return u, len(ulist)-1
    def bfs(self, s, t, level):
        for i in range(len(level)): level[i] = -1
        q = deque([s]); level[s] = 0
        while q:
            u = q.popleft()
            for e in self.g[u]:
                if e.cap > EPS and level[e.to] < 0:
                    level[e.to] = level[u] + 1
                    q.append(e.to)
        return level[t] >= 0
    def dfs(self, u, t, f, level, it):
        if u == t: return f
        for i in range(it[u], len(self.g[u])):
            it[u] = i
            e = self.g[u][i]
            if e.cap > EPS and level[e.to] == level[u] + 1:
                pushed = self.dfs(e.to, t, min(f, e.cap), level, it)
                if pushed > EPS:
                    e.cap -= pushed
                    self.g[e.to][e.rev].cap += pushed
                    return pushed
        return 0.0
    def max_flow(self, s, t):
        flow = 0.0
        level = [-1] * self.n
        while self.bfs(s, t, level):
            it = [0] * self.n
            while True:
                pushed = self.dfs(s, t, 1e18, level, it)
                if pushed <= EPS: break
                flow += pushed
        return flow

# --------------------- Utilities ---------------------
class NameMap:
    def __init__(self):
        self.map = {}
        self.list = []
    def id(self, name):
        if name not in self.map:
            self.map[name] = len(self.list)
            self.list.append(name)
        return self.map[name]
    def name(self, idx):
        return self.list[idx]

# --------------------- Main solver ---------------------

def read_input():
    return json.load(sys.stdin)


def write_output(obj):
    json.dump(obj, sys.stdout, separators=(',',':'))


def solve_belts(inp):
    edges_in = inp.get('edges', [])
    sources = inp.get('sources', {})
    sink = inp.get('sink')
    node_caps = inp.get('node_caps', {})

    # collect all node names deterministically
    nodes = set()
    for e in edges_in:
        nodes.add(e['from']); nodes.add(e['to'])
    nodes |= set(sources.keys())
    if sink is not None:
        nodes.add(sink)
    nodes |= set(node_caps.keys())
    sorted_nodes = sorted(list(nodes))

    nm = NameMap()
    for name in sorted_nodes:
        nm.id(name)

    # We'll perform node-splitting for nodes that have capacity constraints.
    # For determinism we create indices as follows: for each original node in sorted order,
    # we assign an "in" index then an "out" index (if splitting), or single index if no split.

    in_id = {}
    out_id = {}
    idx = 0
    for name in sorted_nodes:
        if name in node_caps and name != sink and name not in sources:
            # split node (note: spec said not for source or sink)
            in_id[name] = idx; idx += 1
            out_id[name] = idx; idx += 1
        else:
            # single node: use one id for both in/out
            in_id[name] = idx
            out_id[name] = idx
            idx += 1
    # super nodes: we'll add two more for s* and t* and later two more for main S and T
    S_star = idx; idx += 1
    T_star = idx; idx += 1
    S_main = idx; idx += 1
    T_main = idx; idx += 1

    N = idx
    dinic = Dinic(N)

    # We'll store mapping from original edges to the forward edge object (node, pos)
    edge_records = []  # tuples: (u_name, v_name, lo, hi, (u_idx, pos_in_g[u_idx]))

    # Step 1: Add node-split cap edges
    node_split_edge_ref = {}  # name -> (u, pos)
    for name in sorted_nodes:
        if in_id[name] != out_id[name]:
            cap = float(node_caps.get(name, 0.0))
            u, pos = dinic.add_edge(in_id[name], out_id[name], cap)
            node_split_edge_ref[name] = (u, pos)

    # Step 2: Add edges with capacity hi - lo, record lo demands
    demand = [0.0] * N  # imbalance caused by lower bounds (on the node indices we chose: use in/out mapping)

    for e in sorted(edges_in, key=lambda x: (x['from'], x['to'])):
        u_name = e['from']; v_name = e['to']
        lo = float(e.get('lo', 0.0)); hi = float(e.get('hi', 0.0))
        if hi + EPS < lo:
            # invalid bounds -> infeasible immediately
            return {'status':'infeasible', 'cut_reachable': [], 'deficit': {'demand_balance': lo-hi, 'tight_nodes': [], 'tight_edges': []}}
        cap = max(0.0, hi - lo)
        u_idx = out_id[u_name]
        v_idx = in_id[v_name]
        u_pos, u_edge_pos = dinic.add_edge(u_idx, v_idx, cap)
        # record forward edge position for later reconstruction: it's at g[u_idx][u_edge_pos]
        edge_records.append((u_name, v_name, lo, hi, (u_idx, u_edge_pos)))
        # accumulate demands
        demand[v_idx] += lo
        demand[u_idx] -= lo

    # Step 3: connect node demands to S* and T*
    total_pos_demand = 0.0
    for i in range(N):
        if abs(demand[i]) <= EPS: continue
        if demand[i] > 0:
            dinic.add_edge(S_star, i, demand[i])
            total_pos_demand += demand[i]
        else:
            dinic.add_edge(i, T_star, -demand[i])

    # Now run maxflow from S* to T* to check lower-bound feasibility (circulation)
    flowed = dinic.max_flow(S_star, T_star)
    if abs(flowed - total_pos_demand) > 1e-6:
        # infeasible lower bounds -> produce certificate derived from min-cut of S* -> T*
        # find reachable from S* in residual graph
        visited = [False]*N
        q = deque([S_star]); visited[S_star] = True
        while q:
            u = q.popleft()
            for e in dinic.g[u]:
                if e.cap > EPS and not visited[e.to]:
                    visited[e.to] = True; q.append(e.to)
        # build cut_reachable using original node names (map in_id/out_id to names)
        reachable_names = set()
        for name in sorted_nodes:
            if visited[in_id[name]] or visited[out_id[name]]:
                reachable_names.add(name)
        # tight edges crossing cut: edges from reachable to unreachable that are saturated (i.e., remaining cap <= EPS)
        tight_edges = []
        for (u_name, v_name, lo, hi, (u_idx, pos)) in edge_records:
            e = dinic.g[u_idx][pos]
            # original capacity of reduced edge = hi-lo
            orig_cap = e.orig
            # if u in reachable and v not
            if (visited[u_idx] and not visited[dinic.g[u_idx][pos].to]):
                # remaining cap e.cap; if saturated
                if e.cap <= EPS:
                    tight_edges.append({'from': u_name, 'to': v_name, 'flow_needed': lo + orig_cap})
        # tight nodes: node-split edges saturated
        tight_nodes = []
        for name, (u,pos) in node_split_edge_ref.items():
            e = dinic.g[u][pos]
            if e.cap <= EPS:
                tight_nodes.append(name)
        deficit = {
            'demand_balance': round((total_pos_demand - flowed), 9),
            'tight_nodes': sorted(tight_nodes),
            'tight_edges': tight_edges
        }
        return {'status':'infeasible', 'cut_reachable': sorted(list(reachable_names)), 'deficit': deficit}

    # Lower bounds feasible. Now remove S* and T* edges from consideration and prepare main flow.
    # We'll keep the current residual capacities (dinic.g contains updated caps after circulation flow).
    # Next, we want to send supplies from sources to sink. Create edges from S_main to each source node (their out id),
    # and from sink node (its in id) to T_main with capacity = total supply.

    total_supply = 0.0
    for sname in sorted(sources.keys()):
        supply = float(sources[sname])
        if supply < -EPS: supply = 0.0
        if sname not in out_id:
            # source not in node set => infeasible
            return {'status':'infeasible','cut_reachable': [], 'deficit': {'demand_balance': supply, 'tight_nodes': [], 'tight_edges': []}}
        if supply > 0:
            dinic.add_edge(S_main, out_id[sname], supply)
            total_supply += supply
    if sink is None or sink not in in_id:
        # invalid sink
        return {'status':'infeasible','cut_reachable': [], 'deficit': {'demand_balance': total_supply, 'tight_nodes': [], 'tight_edges': []}}
    # connect sink to T_main with capacity total_supply
    dinic.add_edge(in_id[sink], T_main, total_supply)

    # Run max flow from S_main to T_main
    pushed = dinic.max_flow(S_main, T_main)
    if abs(pushed - total_supply) > 1e-6:
        # infeasible to send all supply to sink -> produce cut certificate from S_main
        visited = [False]*N
        q = deque([S_main]); visited[S_main]=True
        while q:
            u=q.popleft()
            for e in dinic.g[u]:
                if e.cap > EPS and not visited[e.to]:
                    visited[e.to]=True; q.append(e.to)
        reachable_names = set()
        for name in sorted_nodes:
            if visited[in_id[name]] or visited[out_id[name]]:
                reachable_names.add(name)
        # demand_balance is unsent supply on source side: total_supply - pushed
        tight_edges = []
        for (u_name, v_name, lo, hi, (u_idx, pos)) in edge_records:
            e = dinic.g[u_idx][pos]
            if (visited[u_idx] and not visited[dinic.g[u_idx][pos].to]):
                if e.cap <= EPS:
                    orig_cap = e.orig
                    tight_edges.append({'from': u_name, 'to': v_name, 'flow_needed': lo + orig_cap})
        tight_nodes = []
        for name, (u,pos) in node_split_edge_ref.items():
            e = dinic.g[u][pos]
            if e.cap <= EPS:
                tight_nodes.append(name)
        deficit = {
            'demand_balance': round((total_supply - pushed), 9),
            'tight_nodes': sorted(tight_nodes),
            'tight_edges': tight_edges
        }
        return {'status':'infeasible', 'cut_reachable': sorted(list(reachable_names)), 'deficit': deficit}

    # Success: reconstruct flows for original edges: flow = (orig_cap - current_cap) + lo
    flows = []
    for (u_name, v_name, lo, hi, (u_idx, pos)) in edge_records:
        e = dinic.g[u_idx][pos]
        used = e.orig - e.cap
        final_flow = used + lo
        # clamp small negatives
        if abs(final_flow) < 1e-12: final_flow = 0.0
        flows.append({'from': u_name, 'to': v_name, 'flow': round(final_flow, 9)})

    # compute total delivered to sink
    total_delivered = 0.0
    for f in flows:
        if f['to'] == sink:
            total_delivered += f['flow']

    return {'status':'ok', 'max_flow_per_min': round(total_delivered, 9), 'flows': flows}


if __name__ == '__main__':
    inp = read_input()
    try:
        out = solve_belts(inp)
    except Exception as e:
        out = {'status':'infeasible', 'cut_reachable': [], 'deficit': {'demand_balance': 0.0, 'tight_nodes': [], 'tight_edges': [str(e)]}}
    write_output(out)
