"""State duration allocation and visual transition helpers."""

from typing import Sequence


def allocate_state_durations(
    total_duration: float,
    num_states: int,
    min_state_duration: float = 0.7,
) -> list[float]:
    """Calculate the duration in seconds for each visual state.

    Ensures each state has at least min_state_duration (if total duration allows),
    reducing the number of states if total_duration is too short, and absorbing
    floating point remainder in the final state.
    """
    if num_states <= 1 or total_duration < (min_state_duration * 2):
        return [round(total_duration, 4)]

    max_possible_states = max(1, int(total_duration // min_state_duration))
    actual_states = min(num_states, max_possible_states)

    if actual_states <= 1:
        return [round(total_duration, 4)]

    base_dur = round(total_duration / actual_states, 3)
    durations = [base_dur] * (actual_states - 1)
    last_dur = round(total_duration - sum(durations), 4)
    durations.append(last_dur)
    return durations


def select_progressive_state_indices(
    logical_state_count: int,
    actual_state_count: int,
) -> list[int]:
    """Select a deterministic, ordered list of logical state indices when reduced.

    Invariants:
    - If actual_state_count >= logical_state_count: returns range(logical_state_count).
    - If actual_state_count == 1: returns [logical_state_count - 1] (most complete final state).
    - If actual_state_count > 1: always includes first state (0) and final state (logical_state_count - 1).
    - Strictly preserves ascending order with no duplicates.
    - Result length equals actual_state_count.
    """
    if logical_state_count <= 0 or actual_state_count <= 0:
        return []
    if actual_state_count >= logical_state_count:
        return list(range(logical_state_count))
    if actual_state_count == 1:
        return [logical_state_count - 1]

    n = logical_state_count
    k = actual_state_count
    indices = [int(round(i * (n - 1) / (k - 1))) for i in range(k)]

    # Guarantee strictly monotonic ascending
    for i in range(1, k):
        if indices[i] <= indices[i - 1]:
            indices[i] = indices[i - 1] + 1

    # Guarantee final index is n - 1
    indices[-1] = n - 1
    for i in range(k - 2, -1, -1):
        if indices[i] >= indices[i + 1]:
            indices[i] = indices[i + 1] - 1

    return indices

