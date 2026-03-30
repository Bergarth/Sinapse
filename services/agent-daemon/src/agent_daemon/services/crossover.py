"""Conservative first-pass crossover region ranking."""

from __future__ import annotations

from dataclasses import dataclass

from agent_daemon.services.frd_zma_parser import ParsedTableSummary


@dataclass(frozen=True)
class CrossoverCandidate:
    frequency_hz: float
    score: float
    confidence: str
    warnings: list[str]
    reasoning: str


def rank_first_pass_crossover_regions(
    *,
    frd_summaries: list[ParsedTableSummary],
    zma_summaries: list[ParsedTableSummary],
) -> list[CrossoverCandidate]:
    warnings: list[str] = []
    if not frd_summaries or not zma_summaries:
        return [
            CrossoverCandidate(
                frequency_hz=0.0,
                score=0.0,
                confidence="low",
                warnings=["Need at least one FRD and one ZMA file to propose crossover regions."],
                reasoning="I could not rank crossover regions because measurement coverage is incomplete.",
            )
        ]

    frd_min = min(item.frequency_min_hz or 0.0 for item in frd_summaries if item.frequency_min_hz is not None)
    frd_max = max(item.frequency_max_hz or 0.0 for item in frd_summaries if item.frequency_max_hz is not None)
    zma_min = min(item.frequency_min_hz or 0.0 for item in zma_summaries if item.frequency_min_hz is not None)
    zma_max = max(item.frequency_max_hz or 0.0 for item in zma_summaries if item.frequency_max_hz is not None)
    overlap_min = max(frd_min, zma_min)
    overlap_max = min(frd_max, zma_max)

    if overlap_max <= overlap_min or overlap_min <= 0:
        return [
            CrossoverCandidate(
                frequency_hz=0.0,
                score=0.0,
                confidence="low",
                warnings=["FRD/ZMA frequency ranges do not overlap enough for a conservative estimate."],
                reasoning="No reliable overlap exists between response and impedance ranges.",
            )
        ]

    centers = [0.25, 0.4, 0.55, 0.7]
    candidates: list[CrossoverCandidate] = []
    span = overlap_max - overlap_min
    total_parse_errors = sum(len(item.errors) for item in [*frd_summaries, *zma_summaries])
    total_warnings = sum(len(item.warnings) for item in [*frd_summaries, *zma_summaries])

    if total_parse_errors > 0:
        warnings.append(f"Found {total_parse_errors} parse errors across measurement files.")
    if total_warnings > 0:
        warnings.append(f"Found {total_warnings} parser warnings; treat recommendations as first-pass only.")

    for fraction in centers:
        frequency = overlap_min + (span * fraction)
        mid_penalty = abs(0.5 - fraction) * 20.0
        quality_penalty = min(45.0, (total_parse_errors * 1.5) + (total_warnings * 0.8))
        score = max(0.0, 100.0 - mid_penalty - quality_penalty)
        confidence = "high" if score >= 75 else "medium" if score >= 50 else "low"
        reasoning = (
            f"This candidate sits at {fraction:.0%} of the shared FRD/ZMA frequency overlap "
            f"({overlap_min:.1f} Hz to {overlap_max:.1f} Hz). "
            "Middle-overlap points are favored in this conservative first pass."
        )
        candidates.append(
            CrossoverCandidate(
                frequency_hz=frequency,
                score=round(score, 1),
                confidence=confidence,
                warnings=list(warnings),
                reasoning=reasoning,
            )
        )

    return sorted(candidates, key=lambda item: item.score, reverse=True)
