"""Kiwi (Cassowary) linear constraint layout backend for LearnFlow V2."""

from dataclasses import dataclass
from typing import Any
import kiwisolver

from learnflow_v2.core.errors import LayoutUnsatisfiableError
from learnflow_v2.layout.schema import Rect


# Re-export strengths for explicit readability in constraint definitions
STRENGTH_REQUIRED = kiwisolver.strength.required
STRENGTH_STRONG = kiwisolver.strength.strong
STRENGTH_MEDIUM = kiwisolver.strength.medium
STRENGTH_WEAK = kiwisolver.strength.weak


@dataclass(frozen=True)
class BoxVariables:
    """Kiwi variables corresponding to a single layout item."""

    node_id: str
    x: kiwisolver.Variable
    y: kiwisolver.Variable
    width: kiwisolver.Variable
    height: kiwisolver.Variable

    @property
    def left(self) -> Any:
        return self.x

    @property
    def right(self) -> Any:
        return self.x + self.width

    @property
    def top(self) -> Any:
        return self.y

    @property
    def bottom(self) -> Any:
        return self.y + self.height

    @property
    def center_x(self) -> Any:
        return self.x + 0.5 * self.width

    @property
    def center_y(self) -> Any:
        return self.y + 0.5 * self.height


class KiwiLayoutSolver:
    """Manages Kiwisolver lifecycle, variables, and constraints."""

    def __init__(self, scene_id: str = "unknown") -> None:
        self.scene_id = scene_id
        self._solver = kiwisolver.Solver()
        self._boxes: dict[str, BoxVariables] = {}

    def add_box(self, node_id: str) -> BoxVariables:
        """Register a node with the solver, assigning deterministic variables."""
        if node_id in self._boxes:
            return self._boxes[node_id]
        # Deterministic variable naming aids debugging and inspection
        var_x = kiwisolver.Variable(f"{node_id}_x")
        var_y = kiwisolver.Variable(f"{node_id}_y")
        var_w = kiwisolver.Variable(f"{node_id}_w")
        var_h = kiwisolver.Variable(f"{node_id}_h")
        bv = BoxVariables(
            node_id=node_id,
            x=var_x,
            y=var_y,
            width=var_w,
            height=var_h,
        )
        self._boxes[node_id] = bv
        return bv

    def get_box(self, node_id: str) -> BoxVariables:
        """Retrieve registered box variables for node_id."""
        if node_id not in self._boxes:
            raise KeyError(f"Box for node '{node_id}' not found in solver")
        return self._boxes[node_id]

    def add_constraint(
        self,
        constraint: Any,
        strength: float | None = None,
        stage: str = "layout",
    ) -> None:
        """Add a constraint to Kiwi solver, mapping unsat into LayoutUnsatisfiableError."""
        c = (constraint | strength) if strength is not None else constraint
        try:
            self._solver.addConstraint(c)
        except kiwisolver.UnsatisfiableConstraint as exc:
            raise LayoutUnsatisfiableError(
                f"Constraint unsatisfiable in stage '{stage}': {exc}",
                details={"scene_id": self.scene_id, "stage": stage, "error_type": "UnsatisfiableConstraint"},
            ) from exc
        except kiwisolver.DuplicateConstraint:
            # Duplicate constraint is benign in Cassowary; ignore
            pass

    def solve(self) -> dict[str, Rect]:
        """Solve linear system and extract Rects for all registered boxes."""
        try:
            self._solver.updateVariables()
        except kiwisolver.UnsatisfiableConstraint as exc:
            raise LayoutUnsatisfiableError(
                f"Layout constraints cannot be resolved: {exc}",
                details={"scene_id": self.scene_id, "error_type": "UnsatisfiableConstraint"},
            ) from exc

        results: dict[str, Rect] = {}
        for node_id, bv in self._boxes.items():
            vx = round(float(bv.x.value()), 2)
            vy = round(float(bv.y.value()), 2)
            vw = round(float(bv.width.value()), 2)
            vh = round(float(bv.height.value()), 2)
            if vw <= 0.0 or vh <= 0.0 or vx < 0.0 or vy < 0.0:
                raise LayoutUnsatisfiableError(
                    f"Solved box '{node_id}' produced non-positive or negative dimensions: ({vx}, {vy}, {vw}, {vh})",
                    details={"scene_id": self.scene_id, "node_id": node_id},
                )
            results[node_id] = Rect(x=vx, y=vy, width=vw, height=vh)
        return results
