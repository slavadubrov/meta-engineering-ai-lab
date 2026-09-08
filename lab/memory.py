"""Small stateful target with a bounded configuration-only mutable surface."""

from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import date
from math import isfinite


@dataclass(frozen=True)
class Config:
    min_confidence: float = 0.7
    filter_entity: bool = False
    time_aware: bool = False
    deduplicate: bool = False
    top_k: int = 3

    def patch(self, values: dict) -> "Config":
        if not isinstance(values, dict):
            raise ValueError("A candidate patch must be a JSON object")
        unknown = set(values) - set(asdict(self))
        if unknown:
            raise ValueError(f"Outside the mutable surface: {', '.join(sorted(unknown))}")
        updated = replace(self, **values)
        if type(updated.min_confidence) not in (int, float) or not (
            isfinite(updated.min_confidence) and 0 <= updated.min_confidence <= 1
        ):
            raise ValueError("min_confidence must be a finite number between 0 and 1")
        if type(updated.top_k) is not int or not 1 <= updated.top_k <= 8:
            raise ValueError("top_k must be an integer from 1 through 8")
        for name in ("filter_entity", "time_aware", "deduplicate"):
            if type(getattr(updated, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        return updated


# Immutable admission vocabulary for this structured toy domain, not a general secret detector.
ALLOWED_KEYS = frozenset({"city", "language", "timezone", "delivery", "color", "plan"})
CONTEXT_WORD_BUDGET = 64


def scope(item: dict) -> tuple:
    return item["tenant"], item["user"], item["entity"], item["key"]


def valid_at(item: dict, at: str) -> bool:
    return item["valid_from"] <= at and (item["valid_to"] is None or at < item["valid_to"])


class Memory:
    """Each scenario owns a new in-memory instance; history has half-open validity intervals."""

    def __init__(self, config: Config):
        self.config = config
        self.records: list[dict] = []
        self.next_id = 1

    def snapshot(self) -> list[dict]:
        return deepcopy(self.records)

    def write(self, event: dict) -> dict:
        proposal = event["fact"]
        owner = event["tenant"], event["user"]
        if (proposal["tenant"], proposal["user"]) != owner:
            return {"status": "rejected", "reason": "owner_mismatch", "retained": False}
        if (
            proposal["key"] not in ALLOWED_KEYS
            or proposal["kind"] != "fact"
            or proposal["source"] != "user"
        ):
            return {"status": "rejected", "reason": "prohibited_write", "retained": False}
        if proposal["confidence"] < self.config.min_confidence:
            return {"status": "abstained", "reason": "below_threshold", "retained": False}
        active = [r for r in self.records if scope(r) == scope(proposal) and r["valid_to"] is None]
        if active and proposal["valid_from"] < active[-1]["valid_from"]:
            return {"status": "rejected", "reason": "out_of_order_update", "retained": False}
        if self.config.deduplicate and active and active[-1]["value"] == proposal["value"]:
            return {"status": "deduplicated", "reason": "same_active_value", "retained": True}
        for record in active:
            record["valid_to"] = proposal["valid_from"]
        record = {
            name: proposal[name]
            for name in (
                "tenant",
                "user",
                "entity",
                "key",
                "value",
                "valid_from",
                "confidence",
                "source",
            )
        }
        record.update(
            id=f"m{self.next_id:03d}",
            valid_to=None,
            observed_at=event["at"],
            source_event_id=event["source_event_id"],
        )
        self.next_id += 1
        self.records.append(record)
        return {
            "status": "stored",
            "reason": "admitted",
            "retained": True,
            "record_id": record["id"],
        }

    def delete(self, event: dict) -> dict:
        # Delete every version in this authenticated scope, not just the current value.
        removed = [r["id"] for r in self.records if scope(r) == scope(event)]
        self.records = [r for r in self.records if scope(r) != scope(event)]
        return {"status": "deleted", "record_ids": removed}

    def query(self, event: dict) -> dict:
        # Owner isolation is unconditional: no candidate can switch it off.
        eligible = [
            r for r in self.records if (r["tenant"], r["user"]) == (event["tenant"], event["user"])
        ]
        if self.config.filter_entity:
            eligible = [r for r in eligible if r["entity"] == event["entity"]]
        if self.config.time_aware:
            eligible = [r for r in eligible if valid_at(r, event["as_of"])]
        words = set(event["text"].lower().split())

        def rank(record: dict) -> tuple:
            text = f"{record['entity']} {record['key']} {record['value']}".lower().split()
            relevance = 4 * (record["key"] == event["key"]) + len(words.intersection(text))
            return relevance, record["observed_at"], record["id"]

        retrieved = sorted(eligible, key=rank, reverse=True)[: self.config.top_k]
        packed, count = [], 0
        for record in retrieved:
            size = len(f"{record['entity']} {record['key']} {record['value']}".split())
            if count + size <= CONTEXT_WORD_BUDGET:
                packed.append(record)
                count += size
        # ponytail: frozen first-match consumer; replace with a pinned model for stochastic trials.
        selected = next((r for r in packed if r["key"] == event["key"]), None)
        return {
            "answer": selected["value"] if selected else None,
            "answer_record_id": selected["id"] if selected else None,
            "retrieved_ids": [r["id"] for r in retrieved],
            "packed_ids": [r["id"] for r in packed],
            "context_words": count,
        }


def validate_scenarios(scenarios: list[dict]) -> None:
    """Reject malformed imported fixtures before evaluating any candidate."""
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 64:
        raise ValueError("Expected 1 through 64 scenarios")
    ids = set()
    for scenario in scenarios:
        if scenario["id"] in ids:
            raise ValueError("Scenario IDs must be unique")
        ids.add(scenario["id"])
        if scenario["role"] not in {"search", "evaluation", "adversarial"}:
            raise ValueError("Unknown scenario role")
        if not 1 <= len(scenario["events"]) <= 64:
            raise ValueError("Each scenario needs 1 through 64 events")
        if not any(event["action"] == "query" for event in scenario["events"]):
            raise ValueError("Each scenario needs at least one downstream query")
        for event in scenario["events"]:
            if event["action"] not in {"write", "query", "delete"}:
                raise ValueError("Unknown event action")
            canonical_date(event["at"])
            for name in ("tenant", "user"):
                if not isinstance(event[name], str) or not 1 <= len(event[name]) <= 80:
                    raise ValueError(f"Invalid {name}")
            if event["action"] == "write":
                fact = event["fact"]
                for name in ("tenant", "user", "entity", "key", "value", "source", "kind"):
                    if not isinstance(fact[name], str) or not 1 <= len(fact[name]) <= 256:
                        raise ValueError(f"Invalid fact {name}")
                confidence = fact["confidence"]
                if type(confidence) not in (int, float) or not (
                    isfinite(confidence) and 0 <= confidence <= 1
                ):
                    raise ValueError("Invalid fact confidence")
                canonical_date(fact["valid_from"])
                if type(event["should_retain"]) is not bool:
                    raise ValueError("should_retain must be a boolean")
            else:
                for name in ("entity", "key"):
                    if not isinstance(event[name], str) or not 1 <= len(event[name]) <= 80:
                        raise ValueError(f"Invalid {name}")
                if event["action"] == "query":
                    canonical_date(event["as_of"])
                    if not isinstance(event["text"], str) or not 1 <= len(event["text"]) <= 256:
                        raise ValueError("Invalid query text")
                    if event["expected"] is not None and not isinstance(event["expected"], str):
                        raise ValueError("Expected answer must be a string or null")


def canonical_date(value: str) -> None:
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Dates must use canonical YYYY-MM-DD format")
