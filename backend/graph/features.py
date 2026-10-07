"""
SHERLOCK Backend - Graph Feature Extraction
Computes structural, topological, and behavioral graph metrics for each account:
- pagerank
- clustering_coeff
- shared_device_count
- community_id (via Louvain)
- temporal_burst_score
"""

import networkx as nx
from typing import Dict, List, Any
from collections import defaultdict
import datetime
import numpy as np

class GraphFeatureExtractor:
    def __init__(self):
        pass

    def extract_account_features(
        self,
        G: nx.MultiDiGraph,
        transactions: List[Dict[str, Any]],
        accounts: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, float]]:
        """
        Extract graph and behavioral feature vector for all account nodes in the graph.
        Returns mapping: account_id -> { feature_name: value }
        """
        # 1. Project into a simple DiGraph and undirected Graph for standard algorithms
        simple_di = nx.DiGraph()
        simple_undirected = nx.Graph()
        
        for u, v, data in G.edges(data=True):
            w = float(data.get("weight", 1.0))
            if simple_di.has_edge(u, v):
                simple_di[u][v]["weight"] += w
            else:
                simple_di.add_edge(u, v, weight=w)
                
            if simple_undirected.has_edge(u, v):
                simple_undirected[u][v]["weight"] += w
            else:
                simple_undirected.add_edge(u, v, weight=w)

        # 2. PageRank
        try:
            pagerank_scores = nx.pagerank(simple_di, weight="weight", max_iter=100)
        except Exception:
            pagerank_scores = {n: 1.0 / max(1, len(simple_di)) for n in simple_di.nodes()}

        # 3. Clustering Coefficient (on projected account-account or bipartite)
        try:
            clustering_coeffs = nx.clustering(simple_undirected)
        except Exception:
            clustering_coeffs = {n: 0.0 for n in simple_undirected.nodes()}

        # 4. Louvain Community Detection
        community_mapping = {}
        try:
            communities = nx.algorithms.community.louvain_communities(simple_undirected, seed=42)
            for c_id, comm in enumerate(communities):
                for node in comm:
                    community_mapping[node] = c_id
        except Exception:
            # Fallback if networkx version doesn't support louvain
            try:
                communities = list(nx.connected_components(simple_undirected))
                for c_id, comm in enumerate(communities):
                    for node in comm:
                        community_mapping[node] = c_id
            except Exception:
                community_mapping = {n: 0 for n in simple_undirected.nodes()}

        # 5. Shared Device Count
        # Map device -> set(accounts)
        device_to_accounts = defaultdict(set)
        account_to_devices = defaultdict(set)
        for u, v, data in G.edges(data=True):
            if data.get("relation") == "used_device":
                account_to_devices[u].add(v)
                device_to_accounts[v].add(u)
                
        shared_device_counts = {}
        for acc_id in accounts.keys():
            shared = 0
            for dev in account_to_devices[acc_id]:
                # Number of other accounts sharing this device
                other_users = len(device_to_accounts[dev] - {acc_id})
                shared += other_users
            shared_device_counts[acc_id] = float(shared)

        # 6. Temporal Burst Score
        # Group txns by account and calculate max txns in any 1-hour rolling window
        acc_txns = defaultdict(list)
        for txn in transactions:
            acc_txns[txn["account_id"]].append(txn)

        temporal_burst_scores = {}
        for acc_id, tx_list in acc_txns.items():
            if not tx_list:
                temporal_burst_scores[acc_id] = 0.0
                continue
            
            # Parse timestamps
            times = []
            for t in tx_list:
                try:
                    ts = datetime.datetime.fromisoformat(t["timestamp"])
                    times.append(ts.timestamp())
                except Exception:
                    pass
            times.sort()
            
            if len(times) <= 1:
                temporal_burst_scores[acc_id] = 1.0
                continue
                
            # Sliding window of 3600 seconds (1 hour)
            max_in_hour = 1
            left = 0
            for right in range(len(times)):
                while times[right] - times[left] > 3600:
                    left += 1
                curr_count = right - left + 1
                if curr_count > max_in_hour:
                    max_in_hour = curr_count
            
            # Normalize: max count / total txns
            burst_ratio = max_in_hour / max(1, len(times))
            temporal_burst_scores[acc_id] = float(max_in_hour * burst_ratio)

        # Compile final feature dictionaries for all accounts
        account_features = {}
        for acc_id in accounts.keys():
            account_features[acc_id] = {
                "pagerank": float(pagerank_scores.get(acc_id, 0.0)),
                "clustering_coeff": float(clustering_coeffs.get(acc_id, 0.0)),
                "shared_device_count": float(shared_device_counts.get(acc_id, 0.0)),
                "community_id": float(community_mapping.get(acc_id, 0)),
                "temporal_burst_score": float(temporal_burst_scores.get(acc_id, 0.0)),
                "in_degree": float(G.in_degree(acc_id) if G.has_node(acc_id) else 0.0),
                "out_degree": float(G.out_degree(acc_id) if G.has_node(acc_id) else 0.0),
            }
            
        return account_features
