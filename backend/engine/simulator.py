"""
SHERLOCK Backend - Real-Time Attack Simulation Engine
Injects simulated coordinated fraud ring attacks incrementally over 30 seconds.
Streams real-time updates through WebSocket manager adhering strictly to API_CONTRACT.md.
"""

import asyncio
import datetime
import random
from typing import Dict, Any, Callable, Awaitable

class AttackSimulator:
    def __init__(self, broadcast_callback: Callable[[Dict[str, Any]], Awaitable[None]]):
        self.broadcast = broadcast_callback
        self.is_running = False

    async def run_simulation(
        self,
        attack_type: str = "carousel",
        num_accounts: int = 5,
        total_amount: float = 250000.0,
        ring_id: str = "RING-SIM-001",
        on_transaction_created: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Inject a fraud attack step-by-step over 30 seconds.
        Pushes `new_transaction`, `ring_detected`, and `stats_update` via WebSocket.
        """
        self.is_running = True
        step_count = 10
        delay_per_step = 30.0 / float(step_count)
        
        accounts = [f"ACC-SIM-{i:03d}" for i in range(1, num_accounts + 1)]
        current_amount = float(total_amount)
        
        for step in range(step_count):
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            sender = accounts[step % num_accounts]
            receiver = accounts[(step + 1) % num_accounts]
            
            # Friction peeling
            decay = random.uniform(0.02, 0.04)
            current_amount = round(current_amount * (1.0 - decay), 2)
            
            txn_id = f"TXN-SIM-{random.randint(10000, 99999)}"
            risk_score = round(random.uniform(0.91, 0.98), 2)
            
            explanation = (
                f"🚨 Real-time Injection: Coordinated {attack_type} hop {sender} -> {receiver} "
                f"for ${current_amount:,.2f} with {decay*100:.1f}% peeling friction."
            )
            
            txn_payload = {
                "txn_id": txn_id,
                "timestamp": now,
                "account_id": sender,
                "target_account_id": receiver,
                "amount": current_amount,
                "merchant": f"Simulated P2P Hop {sender}->{receiver}",
                "risk_score": risk_score,
                "is_fraud": True,
                "explanation_preview": explanation
            }
            
            if on_transaction_created:
                on_transaction_created(txn_payload)

            # 1. Broadcast `new_transaction`
            await self.broadcast({
                "type": "new_transaction",
                "data": txn_payload
            })

            # Mid-way or at end, broadcast ring detection
            if step == 4 or step == step_count - 1:
                await self.broadcast({
                    "type": "ring_detected",
                    "data": {
                        "ring_id": ring_id,
                        "pattern_type": attack_type,
                        "member_count": num_accounts,
                        "confidence": 0.97,
                        "detected_at": now
                    }
                })

            await asyncio.sleep(delay_per_step)

        self.is_running = False
