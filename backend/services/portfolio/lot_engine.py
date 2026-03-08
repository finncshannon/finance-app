"""Lot assignment engine — FIFO, LIFO, Average Cost, Specific ID."""

from __future__ import annotations


class LotEngine:
    """Stateless lot assignment methods for SELL transactions."""

    @staticmethod
    def assign_fifo(lots: list[dict], shares_to_sell: float) -> list[tuple[int, float]]:
        """FIFO: sell oldest lots first. Returns [(lot_id, shares_sold)]."""
        assignments: list[tuple[int, float]] = []
        remaining = shares_to_sell

        # lots should already be sorted by date_acquired ASC
        for lot in lots:
            if remaining <= 0:
                break
            available = lot["shares"]
            sell_qty = min(available, remaining)
            assignments.append((lot["id"], sell_qty))
            remaining -= sell_qty

        return assignments

    @staticmethod
    def assign_lifo(lots: list[dict], shares_to_sell: float) -> list[tuple[int, float]]:
        """LIFO: sell newest lots first. Returns [(lot_id, shares_sold)]."""
        assignments: list[tuple[int, float]] = []
        remaining = shares_to_sell

        # Reverse to sell newest first
        for lot in reversed(lots):
            if remaining <= 0:
                break
            available = lot["shares"]
            sell_qty = min(available, remaining)
            assignments.append((lot["id"], sell_qty))
            remaining -= sell_qty

        return assignments

    @staticmethod
    def assign_avg_cost(lots: list[dict], shares_to_sell: float) -> list[tuple[int, float]]:
        """Average Cost: sell proportionally across all lots."""
        total_shares = sum(lot["shares"] for lot in lots)
        if total_shares <= 0:
            return []

        assignments: list[tuple[int, float]] = []
        remaining = shares_to_sell

        for lot in lots:
            proportion = lot["shares"] / total_shares
            sell_qty = min(lot["shares"], round(shares_to_sell * proportion, 6))
            sell_qty = min(sell_qty, remaining)
            if sell_qty > 0:
                assignments.append((lot["id"], sell_qty))
                remaining -= sell_qty

        # Handle rounding remainder — add to first lot
        if remaining > 0.001 and assignments:
            lot_id, qty = assignments[0]
            assignments[0] = (lot_id, qty + remaining)

        return assignments

    @staticmethod
    def assign_specific(
        lots: list[dict], shares_to_sell: float, lot_ids: list[int],
    ) -> list[tuple[int, float]]:
        """Specific ID: sell from user-specified lots."""
        lots_by_id = {lot["id"]: lot for lot in lots}
        assignments: list[tuple[int, float]] = []
        remaining = shares_to_sell

        for lid in lot_ids:
            if remaining <= 0:
                break
            lot = lots_by_id.get(lid)
            if lot is None:
                continue
            sell_qty = min(lot["shares"], remaining)
            assignments.append((lid, sell_qty))
            remaining -= sell_qty

        return assignments

    @staticmethod
    def compute_realized_gain(
        lots_sold: list[tuple[dict, float]], sale_price: float,
    ) -> float:
        """Compute total realized gain from lot assignments.

        lots_sold: list of (lot_dict, shares_sold) tuples
        """
        total_gain = 0.0
        for lot, shares_sold in lots_sold:
            cost_basis = lot["cost_basis_per_share"]
            gain = (sale_price - cost_basis) * shares_sold
            total_gain += gain
        return round(total_gain, 2)
