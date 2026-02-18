"""Precompute network layout for the prototype.

Uses networkx spring_layout to compute x/y positions for all nodes.
Also computes degree and betweenness centrality for the top-200 nodes.

Input: data/persons.json, data/relations.json
Output: data/network.json
"""
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import networkx as nx
except ImportError:
    print('ERROR: networkx not installed. Run: pip install networkx')
    sys.exit(1)

BASE = 'c:/Users/chstn/Desktop/data/DHCraft/Projekte/Git/DoCTA'


def main():
    print('Loading data...')
    with open(f'{BASE}/data/persons.json', encoding='utf-8') as f:
        persons = json.load(f)
    with open(f'{BASE}/data/relations.json', encoding='utf-8') as f:
        relations = json.load(f)
    with open(f'{BASE}/data/places.json', encoding='utf-8') as f:
        places = json.load(f)
    with open(f'{BASE}/data/institutions.json', encoding='utf-8') as f:
        institutions = json.load(f)
    with open(f'{BASE}/data/functions.json', encoding='utf-8') as f:
        functions = json.load(f)

    print(f'  {len(persons)} persons, {len(relations)} relations')
    print(f'  {len(places)} places, {len(institutions)} institutions, {len(functions)} functions')

    # Build graph
    print('Building graph...')
    G = nx.Graph()

    # Add nodes
    for p in persons:
        name = ' '.join(filter(None, [p.get('first_name', ''), p.get('name', '')]))
        G.add_node(f"person-{p['id']}", label=name or '(unbekannt)', type='person')
    for pl in places:
        G.add_node(f"place-{pl['id']}", label=pl.get('label', ''), type='place')
    for inst in institutions:
        G.add_node(f"institution-{inst['id']}", label=inst.get('name', ''), type='institution')
    for func in functions:
        G.add_node(f"function-{func['id']}", label=func.get('name', ''), type='function')

    # Add edges from relations
    edge_count = 0
    for r in relations:
        src = f"{r['subj_type']}-{r['subj_id']}" if r['subj_id'] else None
        tgt = f"{r['obj_type']}-{r['obj_id']}" if r['obj_id'] else None
        if src and tgt and G.has_node(src) and G.has_node(tgt):
            G.add_edge(src, tgt, rel_type=r.get('relation_type', ''))
            edge_count += 1

    print(f'  Graph: {G.number_of_nodes()} nodes, {edge_count} edges')

    # Get top-200 by degree
    degree = dict(G.degree())
    top_nodes = sorted(degree.keys(), key=lambda x: degree[x], reverse=True)[:200]
    top_set = set(top_nodes)

    print(f'  Top-200 nodes selected (min degree: {degree[top_nodes[-1]] if top_nodes else 0})')

    # Create subgraph for top-200
    sub = G.subgraph(top_set).copy()
    print(f'  Subgraph: {sub.number_of_nodes()} nodes, {sub.number_of_edges()} edges')

    # Compute layout
    print('Computing layout (spring_layout)...')
    pos = nx.spring_layout(sub, k=2.0, iterations=100, seed=42)

    # Compute betweenness centrality for top nodes
    print('Computing betweenness centrality...')
    betweenness = nx.betweenness_centrality(sub)

    # Build output
    network = {
        'nodes': [],
        'metadata': {
            'totalNodes': G.number_of_nodes(),
            'totalEdges': edge_count,
            'displayedNodes': len(top_nodes),
            'layoutAlgorithm': 'spring_layout',
        },
    }

    for node_id in top_nodes:
        data = G.nodes[node_id]
        x, y = pos.get(node_id, (0, 0))
        network['nodes'].append({
            'id': node_id,
            'label': data.get('label', ''),
            'type': data.get('type', ''),
            'x': round(float(x), 4),
            'y': round(float(y), 4),
            'degree': degree.get(node_id, 0),
            'betweenness': round(float(betweenness.get(node_id, 0)), 6),
        })

    # Save
    out_path = f'{BASE}/data/network.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(network, f, ensure_ascii=False, indent=1)

    print(f'\nSaved to {out_path}')
    print(f'  Top-5 by degree:')
    sorted_nodes = sorted(network['nodes'], key=lambda n: n['degree'], reverse=True)
    for n in sorted_nodes[:5]:
        print(f"    {n['label']:<40} degree={n['degree']:>4}  betweenness={n['betweenness']:.4f}")


if __name__ == '__main__':
    main()
