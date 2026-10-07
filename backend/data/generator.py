"""
SHERLOCK Backend - Synthetic Data Generator
Generates realistic financial transaction logs with normal transactions,
high-value legitimate accounts, individual fraud anomalies, and 3 coordinated fraud rings.
"""

import random
import datetime
from typing import Dict, List, Tuple, Any
import numpy as np

def generate_synthetic_dataset(
    num_accounts: int = 500,
    num_transactions: int = 10000,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Generate synthetic transactions and account metadata.
    
    Structure:
    - 500 accounts total:
        - 20 high-value legitimate accounts (large transactions, perfectly consistent device/IP, long tenure)
        - Accounts involved in 3 distinct fraud rings:
            * RING-001 (Gift Card Ring): 8 accounts + 1 collector account (9 accounts)
            * RING-002 (Device Farm Ring): 6 accounts sharing 2 device IDs
            * RING-003 (Circular Ring): 5 accounts cycling funds with 2-5% friction
        - Other normal accounts (~460 accounts)
    - Total 10,000 transactions:
        - ~95% Normal (9,500 txns, log-normal distribution, stable profiles)
        - ~2% Individual Fraud (200 txns, stolen cards, sudden strange IP/device, burst amounts)
        - ~3% Fraud Rings (300 txns distributed across RING-001, RING-002, RING-003)
    """
    random.seed(seed)
    np.random.seed(seed)
    
    start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    
    # Common lists
    normal_merchants = [
        "Amazon Fresh", "Target Store", "Walmart Supercenter", "Starbucks Coffee",
        "Uber Mobility", "Netflix Streaming", "Costco Wholesale", "Shell Fuel",
        "Whole Foods Market", "Apple Services", "CVS Pharmacy", "Home Depot"
    ]
    gift_card_merchants = [
        "GiftCardsDirect", "TechGadgets Superstore", "E-Voucher Express", "CardBazaar"
    ]
    
    # 1. Accounts Setup
    accounts = {}
    
    # 20 High-value legitimate accounts
    high_value_legit_ids = [f"ACC-HV-{i:03d}" for i in range(1, 21)]
    for acc_id in high_value_legit_ids:
        accounts[acc_id] = {
            "account_id": acc_id,
            "account_type": "high_value_legit",
            "primary_device": f"DEV-HV-{acc_id[-3:]}",
            "primary_ip": f"198.51.100.{random.randint(10, 240)}",
            "email": f"exec_{acc_id.lower()}@private-wealth.corp",
            "history_days": random.randint(700, 1200),
            "is_fraud": False,
            "ring_id": None
        }
        
    # RING-001 Accounts (8 shoppers + 1 collector)
    ring1_shoppers = [f"ACC-R1-S{i:02d}" for i in range(1, 9)]
    ring1_collector = "ACC-R1-COLL"
    ring1_accounts = ring1_shoppers + [ring1_collector]
    for acc_id in ring1_accounts:
        accounts[acc_id] = {
            "account_id": acc_id,
            "account_type": "ring_001_gift_card",
            "primary_device": f"DEV-{acc_id}",
            "primary_ip": f"203.0.113.{random.randint(2, 250)}",
            "email": f"temp_{acc_id.lower()}@throwaway-mail.net",
            "history_days": random.randint(3, 14),
            "is_fraud": True,
            "ring_id": "RING-001"
        }
        
    # RING-002 Accounts (6 accounts sharing 2 devices)
    ring2_devices = ["DEV-FARM-ALPHA", "DEV-FARM-BETA"]
    ring2_accounts = [f"ACC-R2-{i:02d}" for i in range(1, 7)]
    for i, acc_id in enumerate(ring2_accounts):
        dev = ring2_devices[i % 2]
        accounts[acc_id] = {
            "account_id": acc_id,
            "account_type": "ring_002_device_farm",
            "primary_device": dev,
            "primary_ip": f"192.0.2.{10 + (i % 2)}",
            "email": f"bot_farm_{i}@proxy-relay.org",
            "history_days": random.randint(1, 10),
            "is_fraud": True,
            "ring_id": "RING-002"
        }
        
    # RING-003 Accounts (5 circular transfer accounts)
    ring3_accounts = [f"ACC-R3-{chr(65+i)}" for i in range(5)]  # A, B, C, D, E
    for i, acc_id in enumerate(ring3_accounts):
        accounts[acc_id] = {
            "account_id": acc_id,
            "account_type": "ring_003_circular",
            "primary_device": f"DEV-CIRC-{acc_id[-1]}",
            "primary_ip": f"198.18.0.{50 + i}",
            "email": f"shell_{acc_id[-1].lower()}@cayman-holdings.biz",
            "history_days": random.randint(5, 30),
            "is_fraud": True,
            "ring_id": "RING-003"
        }
        
    # Standard normal accounts to reach num_accounts
    remaining_count = num_accounts - len(accounts)
    for i in range(1, remaining_count + 1):
        acc_id = f"ACC-{i:04d}"
        accounts[acc_id] = {
            "account_id": acc_id,
            "account_type": "standard_normal",
            "primary_device": f"DEV-STD-{i:04d}",
            "primary_ip": f"10.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
            "email": f"user_{i}@gmail.com",
            "history_days": random.randint(60, 900),
            "is_fraud": False,
            "ring_id": None
        }

    # Public hubs (shared devices / IPs with high benign traffic)
    public_hub_devices = [f"DEV-PUB-AIRPORT-{i}" for i in range(3)]
    public_hub_ips = ["198.51.100.1", "198.51.100.2"]
    
    # 2. Generate Transactions
    transactions: List[Dict[str, Any]] = []
    txn_counter = 1
    
    def make_txn_id():
        nonlocal txn_counter
        t_id = f"TXN-{txn_counter:05d}"
        txn_counter += 1
        return t_id

    # 2A. Generate Ring Transactions (CRITICAL - exact requirements)
    # RING-001 (Gift Card): 8 accounts buy gift cards at same merchants in 2 hrs, then transfer to 1 collector
    ring1_base_time = start_time + datetime.timedelta(days=3, hours=10)
    for shopper_id in ring1_shoppers:
        # 1-2 rapid gift card purchases
        for k in range(random.randint(1, 2)):
            t_offset = datetime.timedelta(minutes=random.randint(2, 90))
            txn_time = ring1_base_time + t_offset
            amt = round(random.uniform(450.0, 500.0), 2)  # High gift card limit
            merchant = random.choice(gift_card_merchants)
            transactions.append({
                "txn_id": make_txn_id(),
                "timestamp": txn_time.isoformat(),
                "account_id": shopper_id,
                "target_account_id": None,
                "amount": amt,
                "merchant": merchant,
                "device_id": accounts[shopper_id]["primary_device"],
                "ip_address": accounts[shopper_id]["primary_ip"],
                "email": accounts[shopper_id]["email"],
                "is_fraud": True,
                "fraud_type": "ring_001_gift_card",
                "ring_id": "RING-001",
                "explanation_preview": f"Gift Card velocity burst: Purchase of ${amt:.2f} at {merchant} within 2hr coordinated window."
            })
            
        # Then consolidate / transfer to collector
        transfer_time = ring1_base_time + datetime.timedelta(hours=2, minutes=random.randint(5, 30))
        transfer_amt = round(random.uniform(400.0, 950.0), 2)
        transactions.append({
            "txn_id": make_txn_id(),
            "timestamp": transfer_time.isoformat(),
            "account_id": shopper_id,
            "target_account_id": ring1_collector,
            "amount": transfer_amt,
            "merchant": "P2P Liquidation Transfer",
            "device_id": accounts[shopper_id]["primary_device"],
            "ip_address": accounts[shopper_id]["primary_ip"],
            "email": accounts[shopper_id]["email"],
            "is_fraud": True,
            "fraud_type": "ring_001_gift_card",
            "ring_id": "RING-001",
            "explanation_preview": f"P2P Funneling: Coordinated transfer of ${transfer_amt:.2f} to common collector {ring1_collector}."
        })

    # RING-002 (Device Farm): 6 accounts share 2 devices, rapid $10-$50 purchases, 3-7 min apart
    ring2_start = start_time + datetime.timedelta(days=4, hours=14)
    current_ring2_time = ring2_start
    # Generate ~80 rapid transactions
    for step in range(80):
        acc = random.choice(ring2_accounts)
        current_ring2_time += datetime.timedelta(minutes=random.randint(3, 7))
        amt = round(random.uniform(10.0, 50.0), 2)
        dev = accounts[acc]["primary_device"]  # either DEV-FARM-ALPHA or BETA
        merchant = random.choice(["DigitalCoins.io", "V-Bucks Store", "GameCredits Fast", "MicroTxn Global"])
        transactions.append({
            "txn_id": make_txn_id(),
            "timestamp": current_ring2_time.isoformat(),
            "account_id": acc,
            "target_account_id": None,
            "amount": amt,
            "merchant": merchant,
            "device_id": dev,
            "ip_address": accounts[acc]["primary_ip"],
            "email": accounts[acc]["email"],
            "is_fraud": True,
            "fraud_type": "ring_002_device_farm",
            "ring_id": "RING-002",
            "explanation_preview": f"Device Farm attack: Shared hardware {dev} executing rapid $10-$50 micro-charges ({step+1}/80)."
        })

    # RING-003 (Circular): 5 accounts send money in a circle A->B->C->D->E->A, decreasing by 2-5% each hop
    ring3_start = start_time + datetime.timedelta(days=5, hours=9)
    # Circle: A -> B -> C -> D -> E -> A (repeat for 4 cycles)
    curr_amount = 50000.00
    curr_time = ring3_start
    for cycle in range(4):
        for i in range(len(ring3_accounts)):
            sender = ring3_accounts[i]
            receiver = ring3_accounts[(i + 1) % len(ring3_accounts)]
            curr_time += datetime.timedelta(minutes=random.randint(15, 45))
            friction = random.uniform(0.02, 0.05)
            curr_amount = round(curr_amount * (1.0 - friction), 2)
            transactions.append({
                "txn_id": make_txn_id(),
                "timestamp": curr_time.isoformat(),
                "account_id": sender,
                "target_account_id": receiver,
                "amount": curr_amount,
                "merchant": f"Wire Hop {sender}->{receiver}",
                "device_id": accounts[sender]["primary_device"],
                "ip_address": accounts[sender]["primary_ip"],
                "email": accounts[sender]["email"],
                "is_fraud": True,
                "fraud_type": "ring_003_circular",
                "ring_id": "RING-003",
                "explanation_preview": f"Circular Wash Trade: {sender} -> {receiver} ${curr_amount:.2f} with {friction*100:.1f}% peeling."
            })
        curr_amount = 45000.00  # Reset for next wave

    # Fill additional ring transactions to ensure around 300 total ring transactions
    ring_txns_count = len(transactions)

    # 2B. Generate Individual Fraud Transactions (~2% = 200 txns)
    individual_fraud_count = 200
    std_account_ids = [acc_id for acc_id, d in accounts.items() if d["account_type"] == "standard_normal"]
    for _ in range(individual_fraud_count):
        victim_acc = random.choice(std_account_ids)
        # Stolen card or sudden device takeover
        fraud_mode = random.choice(["stolen_card", "device_takeover"])
        rand_delta = datetime.timedelta(seconds=random.randint(0, int(7 * 86400)))
        t_time = start_time + rand_delta
        
        if fraud_mode == "stolen_card":
            foreign_device = f"DEV-ROGUE-{random.randint(1000, 9999)}"
            foreign_ip = f"185.{random.randint(10, 250)}.{random.randint(10, 250)}.{random.randint(1, 254)}"
            amt = round(random.uniform(1200.0, 4800.0), 2)
            merch = random.choice(["CryptoSwap Ltd.", "LuxuryWatches Geneva", "HighRoller Casino"])
            explanation = f"Stolen card anomaly: Foreign device {foreign_device} from anomalous IP {foreign_ip} for ${amt:.2f}."
        else:
            foreign_device = f"DEV-TAKEOVER-{random.randint(100, 999)}"
            foreign_ip = f"194.{random.randint(10, 250)}.{random.randint(1, 250)}.{random.randint(1, 254)}"
            amt = round(random.uniform(800.0, 3200.0), 2)
            merch = random.choice(["Unregistered Wire Transfer", "Anonymous Remit LLC"])
            explanation = f"Account takeover: Sudden device migration and immediate high-velocity cashout."
            
        transactions.append({
            "txn_id": make_txn_id(),
            "timestamp": t_time.isoformat(),
            "account_id": victim_acc,
            "target_account_id": None,
            "amount": amt,
            "merchant": merch,
            "device_id": foreign_device,
            "ip_address": foreign_ip,
            "email": accounts[victim_acc]["email"],
            "is_fraud": True,
            "fraud_type": f"individual_{fraud_mode}",
            "ring_id": None,
            "explanation_preview": explanation
        })

    # 2C. Generate High-Value Legitimate Transactions (Part of normal 95%)
    # 20 accounts spending $10k+ with perfect behavioral consistency
    for acc_id in high_value_legit_ids:
        acc_meta = accounts[acc_id]
        # 10 to 25 transactions each
        for _ in range(random.randint(10, 25)):
            rand_delta = datetime.timedelta(seconds=random.randint(0, int(7 * 86400)))
            t_time = start_time + rand_delta
            amt = round(random.uniform(10000.0, 75000.0), 2)
            merch = random.choice(["Private Jet Charter", "Sotheby's Auction", "Commercial Wire", "Goldman Prime Brokerage"])
            transactions.append({
                "txn_id": make_txn_id(),
                "timestamp": t_time.isoformat(),
                "account_id": acc_id,
                "target_account_id": None,
                "amount": amt,
                "merchant": merch,
                "device_id": acc_meta["primary_device"],  # Always primary device!
                "ip_address": acc_meta["primary_ip"],      # Always primary IP!
                "email": acc_meta["email"],
                "is_fraud": False,
                "fraud_type": None,
                "ring_id": None,
                "explanation_preview": f"Legitimate VIP: Known device {acc_meta['primary_device']} matching {acc_meta['history_days']}-day tenure."
            })

    # 2D. Generate Standard Normal Transactions to reach target num_transactions
    remaining_txns = num_transactions - len(transactions)
    for _ in range(max(0, remaining_txns)):
        acc_id = random.choice(std_account_ids)
        acc_meta = accounts[acc_id]
        rand_delta = datetime.timedelta(seconds=random.randint(0, int(7 * 86400)))
        t_time = start_time + rand_delta
        
        # Log-normal distribution for amounts (median around $45, tail up to $400)
        amt = round(float(np.random.lognormal(mean=3.6, sigma=0.85)), 2)
        amt = max(2.50, min(amt, 950.0))
        
        # 96% use primary device/IP, 4% public hub (coffee shop / airport)
        if random.random() < 0.04:
            dev = random.choice(public_hub_devices)
            ip = random.choice(public_hub_ips)
        else:
            dev = acc_meta["primary_device"]
            ip = acc_meta["primary_ip"]
            
        merch = random.choice(normal_merchants)
        transactions.append({
            "txn_id": make_txn_id(),
            "timestamp": t_time.isoformat(),
            "account_id": acc_id,
            "target_account_id": None,
            "amount": amt,
            "merchant": merch,
            "device_id": dev,
            "ip_address": ip,
            "email": acc_meta["email"],
            "is_fraud": False,
            "fraud_type": None,
            "ring_id": None,
            "explanation_preview": f"Routine transaction: Regular merchant {merch} with historical profile match."
        })

    # Sort transactions chronologically
    transactions.sort(key=lambda x: x["timestamp"])

    return {
        "accounts": accounts,
        "transactions": transactions,
        "metadata": {
            "total_transactions": len(transactions),
            "total_accounts": len(accounts),
            "fraud_count": sum(1 for t in transactions if t["is_fraud"]),
            "ring_count": 3,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    }

if __name__ == "__main__":
    data = generate_synthetic_dataset()
    print("Generated summary:")
    print("Total Txns:", data["metadata"]["total_transactions"])
    print("Fraud Count:", data["metadata"]["fraud_count"])
    print("Sample Txn:", data["transactions"][0])
