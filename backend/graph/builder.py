"""
SHERLOCK Backend - Graph Builder
Constructs a heterogeneous graph from accounts and transaction records using NetworkX.
Entities: account, device, merchant, ip, email.
Edges: used_device, used_ip, used_email, transacted_at, transferred_to.
Handles 'public hub' discounting when devices/IPs are shared by >50 accounts.
"""

from typing import Dict, List, Any, Optional
import networkx as nx
from collections import defaultdict

class TransactionGraphBuilder:
    def __init__(self, public_hub_threshold: int = 50):
        self.public_hub_threshold = public_hub_threshold
        self.graph = nx.MultiDiGraph()
        
    def build_graph(
        self,
        accounts: Dict[str, Dict[str, Any]],
        transactions: List[Dict[str, Any]]
    ) -> nx.MultiDiGraph:
        """
        Build the heterogeneous networkx graph from accounts and transactions.
        """
        self.graph = nx.MultiDiGraph()
        
        # 1. Add account nodes
        for acc_id, meta in accounts.items():
            self.graph.add_node(
                acc_id,
                node_type="account",
                label=acc_id,
                account_type=meta.get("account_type", "normal"),
                is_fraud=meta.get("is_fraud", False),
                ring_id=meta.get("ring_id"),
                risk_score=0.9 if meta.get("is_fraud") else 0.05,
                history_days=meta.get("history_days", 30)
            )
            
        # 2. Track entity usage to identify public hubs
        device_users = defaultdict(set)
        ip_users = defaultdict(set)
        
        for txn in transactions:
            acc_id = txn["account_id"]
            if txn.get("device_id"):
                device_users[txn["device_id"]].add(acc_id)
            if txn.get("ip_address"):
                ip_users[txn["ip_address"]].add(acc_id)
                
        # 3. Add entities and edges from transactions
        for txn in transactions:
            acc_id = txn["account_id"]
            txn_id = txn["txn_id"]
            amount = float(txn["amount"])
            ts = txn["timestamp"]
            is_fraud = txn.get("is_fraud", False)
            ring_id = txn.get("ring_id")
            
            # Target account (P2P transfer) or Merchant
            target_acc = txn.get("target_account_id")
            merchant = txn.get("merchant")
            device_id = txn.get("device_id")
            ip_addr = txn.get("ip_address")
            email = txn.get("email")
            
            # Device node & edge
            if device_id:
                is_hub = len(device_users[device_id]) > self.public_hub_threshold
                weight = 0.1 if is_hub else 1.0
                if not self.graph.has_node(device_id):
                    self.graph.add_node(
                        device_id,
                        node_type="device",
                        label=device_id,
                        is_hub=is_hub,
                        user_count=len(device_users[device_id])
                    )
                self.graph.add_edge(
                    acc_id, device_id,
                    key=f"dev_{txn_id}",
                    relation="used_device",
                    weight=weight,
                    timestamp=ts,
                    txn_id=txn_id
                )
                
            # IP node & edge
            if ip_addr:
                is_hub = len(ip_users[ip_addr]) > self.public_hub_threshold
                weight = 0.1 if is_hub else 1.0
                if not self.graph.has_node(ip_addr):
                    self.graph.add_node(
                        ip_addr,
                        node_type="ip",
                        label=ip_addr,
                        is_hub=is_hub,
                        user_count=len(ip_users[ip_addr])
                    )
                self.graph.add_edge(
                    acc_id, ip_addr,
                    key=f"ip_{txn_id}",
                    relation="used_ip",
                    weight=weight,
                    timestamp=ts,
                    txn_id=txn_id
                )
                
            # Email node & edge
            if email:
                if not self.graph.has_node(email):
                    self.graph.add_node(
                        email,
                        node_type="email",
                        label=email
                    )
                self.graph.add_edge(
                    acc_id, email,
                    key=f"email_{txn_id}",
                    relation="used_email",
                    weight=1.0,
                    timestamp=ts,
                    txn_id=txn_id
                )

            # Direct transfer edge between accounts
            if target_acc and target_acc in accounts:
                self.graph.add_edge(
                    acc_id, target_acc,
                    key=f"transfer_{txn_id}",
                    relation="transferred_to",
                    amount=amount,
                    weight=1.0,
                    timestamp=ts,
                    txn_id=txn_id,
                    is_fraud=is_fraud,
                    ring_id=ring_id
                )
            elif merchant:
                # Merchant node & transaction edge
                if not self.graph.has_node(merchant):
                    self.graph.add_node(
                        merchant,
                        node_type="merchant",
                        label=merchant
                    )
                self.graph.add_edge(
                    acc_id, merchant,
                    key=f"merch_{txn_id}",
                    relation="transacted_at",
                    amount=amount,
                    weight=1.0,
                    timestamp=ts,
                    txn_id=txn_id,
                    is_fraud=is_fraud,
                    ring_id=ring_id
                )
                
        return self.graph

    def to_cytoscape_json(self, max_nodes: int = 400, filter_ring_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export graph in standard Cytoscape.js JSON format required by API_CONTRACT.md.
        { "elements": { "nodes": [...], "edges": [...] } }
        """
        nodes_data = []
        edges_data = []
        
        # Priority to accounts and fraud entities
        included_nodes = set()
        
        # If filtering for a specific ring
        if filter_ring_id:
            for n, data in self.graph.nodes(data=True):
                if data.get("ring_id") == filter_ring_id or filter_ring_id in str(data.get("label", "")):
                    included_nodes.add(n)
            # Add 1-hop neighbors
            neighbors = set()
            for n in included_nodes:
                neighbors.update(self.graph.neighbors(n))
                if self.graph.is_directed():
                    neighbors.update(self.graph.predecessors(n))
            included_nodes.update(neighbors)
        else:
            # Add all fraud nodes first, then normal accounts up to max_nodes
            fraud_accounts = [n for n, d in self.graph.nodes(data=True) if d.get("is_fraud")]
            included_nodes.update(fraud_accounts)
            
            other_accounts = [n for n, d in self.graph.nodes(data=True) if d.get("node_type") == "account" and n not in included_nodes]
            included_nodes.update(other_accounts[:max(0, max_nodes - len(included_nodes))])
            
            # Include connected devices and merchants
            connected_entities = set()
            for n in list(included_nodes)[:100]:
                for nbr in self.graph.neighbors(n):
                    if self.graph.nodes[nbr].get("node_type") in ("device", "merchant"):
                        connected_entities.add(nbr)
            included_nodes.update(connected_entities)

        for n in included_nodes:
            d = self.graph.nodes[n]
            node_dict = {
                "id": str(n),
                "label": str(d.get("label", n)),
                "node_type": d.get("node_type", "account"),
                "is_fraud": bool(d.get("is_fraud", False)),
                "risk_score": float(d.get("risk_score", 0.1)),
                "ring_id": d.get("ring_id")
            }
            nodes_data.append({"data": node_dict})

        edge_counter = 0
        seen_edges = set()
        for u, v, k, d in self.graph.edges(keys=True, data=True):
            if u in included_nodes and v in included_nodes:
                edge_id = f"e_{u}_{v}_{edge_counter}"
                edge_counter += 1
                edge_key = (u, v, d.get("relation"))
                if edge_key in seen_edges and len(seen_edges) > 500:
                    continue
                seen_edges.add(edge_key)
                
                edge_dict = {
                    "id": edge_id,
                    "source": str(u),
                    "target": str(v),
                    "relation": d.get("relation", "connected"),
                    "amount": float(d.get("amount", 0.0)),
                    "is_suspicious": bool(d.get("is_fraud", False)),
                    "weight": float(d.get("weight", 1.0))
                }
                edges_data.append({"data": edge_dict})
                
        return {
            "elements": {
                "nodes": nodes_data,
                "edges": edges_data
            }
        }
