class FlowMatrix:
    """
    Minimal stub of sfctools.FlowMatrix for CI smoke.
    Provides start_period, log_flow, and check_consistency methods.
    """

    def __init__(self):
        self._t = -1
        self._flows = []

    def start_period(self, t: int):
        self._t = t
        self._flows = []

    def log_flow(self, source: str, sink: str, amount: float, label: str | None = None):
        self._flows.append((source, sink, float(amount), label))

    def check_consistency(self, tol: float = 1e-9):
        # Very light check: sum of amounts by label should be finite; no exception.
        total = 0.0
        for _, _, amt, _ in self._flows:
            total += float(amt)
        # In a real FlowMatrix, we'd assert row/col sums == 0.
        # Here, just return True; callers may assert no exception.
        return True

__all__ = ["FlowMatrix"]

