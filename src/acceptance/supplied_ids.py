"""Holding a model to the ids it was given (#163).

Several stages paste a set of ids into the prompt — obligation ids, test ids,
diff-hunk labels — and ask the model to echo the relevant ones back. Typed as
free-form `str`, an id that does not exist is valid output. The mapping stage
once answered about obligations it had read out of the *test sources* pasted
into its own prompt; the foreign ids were then filtered out silently, leaving a
result indistinguishable from "no test evidences any obligation". The review
told the reader their change was untested when the truth was that the reviewer
had answered a different question.

Two mechanisms, deliberately separate:

- `constrain` puts the supplied ids into the response schema as an enum, built
  per call. Under constrained decoding a foreign id is not merely detected but
  **unrepresentable** — the tokens are not available. This is the enforcement,
  and it is the #158 lesson applied one level further: encode the constraint
  where the model is bound by it, not in the prose.
- `unsupplied` checks returned ids against the supplied set locally. This is
  detection, and it is not redundant with the schema. The harness routes through
  LiteLLM with `drop_params=True` precisely so it can run against providers whose
  structured-output support differs, and a provider that ignores the enum would
  otherwise put us straight back where we started.

The local check is deliberately **per item**. `ModelClient._validate` parses the
whole response object, so constraining the model it parses *with* would turn one
bad id in a 96-entry batch into an aborted review, discarding the 95 usable
judgments that came back alongside it. Hence the `parse_as` seam on
`ModelClient.complete`: the constrained schema is what we ask for, a permissive
one is what we parse with, and the difference between them is recorded rather
than dropped. Dropping is what made the original defect invisible.
"""

from __future__ import annotations

from collections.abc import Container, Iterable, Mapping, Sequence
from typing import Any, Literal, TypeVar, get_args, get_origin

from pydantic import BaseModel, create_model

ModelT = TypeVar("ModelT", bound=BaseModel)


def _literal(ids: Sequence[str]) -> Any:
    return Literal[tuple(ids)]  # type: ignore[valid-type]


def _constrained_field(annotation: Any, ids: Sequence[str]) -> Any:
    """`str` -> one supplied id; `list[str]` -> a list of supplied ids."""
    if annotation is str:
        return _literal(ids)
    if get_origin(annotation) is list and get_args(annotation) == (str,):
        return list[_literal(ids)]  # type: ignore[misc]
    raise TypeError(
        f"cannot constrain a field annotated {annotation!r}: "
        "expected `str` or `list[str]`"
    )


def _constrained_nested(annotation: Any, allowed: Mapping[str, Sequence[str]]) -> Any:
    """Constrain id fields on a nested response model; None if nothing changed.

    The id fields live on the *item* model (`_TestMapping.obligation_ids`), not
    on the container the call returns (`_Mappings.mappings`), so the walk has to
    descend rather than look only at top-level fields.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        nested = constrain(annotation, allowed)
        return None if nested is annotation else nested
    if get_origin(annotation) is list:
        args = get_args(annotation)
        item = args[0] if args else None
        if isinstance(item, type) and issubclass(item, BaseModel):
            nested = constrain(item, allowed)
            return None if nested is item else list[nested]  # type: ignore[valid-type]
    return None


def constrain(model: type[ModelT], allowed: Mapping[str, Sequence[str]]) -> type[ModelT]:
    """Return `model` with each named id field restricted to the ids supplied.

    `allowed` maps a field name to the ids that call actually supplied — built
    per call, never from a fixed list, so a partitioned stage constrains each
    call to its own partition.

    A field whose supplied set is **empty** is left unconstrained: `Literal[]` is
    not a type, and a call that offered no ids has nothing to enforce. The
    guarantee degrades to `unsupplied`'s local detection rather than vanishing.

    The result is a subclass, so it satisfies every use of the original model,
    and it deliberately keeps the same `__name__`: that name is the schema name
    in the request, which the transcript key hashes and the test doubles
    dispatch on.
    """
    overrides: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        if name in allowed:
            ids = list(allowed[name])
            if ids:
                overrides[name] = (_constrained_field(field.annotation, ids), ...)
            continue
        nested = _constrained_nested(field.annotation, allowed)
        if nested is not None:
            overrides[name] = (nested, ...)
    if not overrides:
        return model
    return create_model(model.__name__, __base__=model, **overrides)


class UnusableAnswer(BaseModel):
    """A returned id that was never supplied to the call that returned it.

    Kept rather than dropped: an id we cannot honour means the judgment we asked
    for was not obtained, which is a different thing from the model considering
    the question and answering it negatively. Dropping the two together is what
    made the original defect invisible.
    """

    stage: str
    field: str
    returned_id: str


class UnusableAnswerLog:
    """Unusable answers accumulated across the stages of one review run.

    Passed down rather than returned because six stages produce these and their
    return types are otherwise unrelated; an optional accumulator keeps each
    signature additive. The pipeline owns the instance, so a stage cannot quietly
    decline to report — and a test that the pipeline actually passes one is part
    of this task's wiring, not an extra.
    """

    def __init__(self) -> None:
        self.answers: list[UnusableAnswer] = []
        self.indeterminate_obligations: set[str] = set()

    def record(self, answers: Iterable[UnusableAnswer]) -> list[UnusableAnswer]:
        found = list(answers)
        self.answers.extend(found)
        return found

    def mark_indeterminate(self, obligation_ids: Iterable[str]) -> None:
        """Obligations whose judgment was not obtained, so it cannot be reported
        as a substantive finding about their evidence."""
        self.indeterminate_obligations.update(obligation_ids)

    def __bool__(self) -> bool:
        return bool(self.answers)


def scan(
    response: BaseModel,
    allowed: Mapping[str, Sequence[str]],
    stage: str,
) -> list[UnusableAnswer]:
    """Every id in `response` that `allowed` never supplied, in traversal order.

    Walks the whole response tree so it finds id fields on nested item models,
    which is where they all live — the container a call returns holds a list of
    judgments, and the ids are on the judgments.

    This is the detection half of the guarantee, and it runs even when
    `constrain` already put the ids in the schema: `constrain` binds providers
    that honour structured output, and the harness deliberately runs against
    providers whose support differs.
    """
    supplied = {field: set(ids) for field, ids in allowed.items()}
    found: list[UnusableAnswer] = []
    seen: set[tuple[str, str]] = set()

    def visit(node: Any) -> None:
        if isinstance(node, BaseModel):
            for name, _ in type(node).model_fields.items():
                value = getattr(node, name)
                if name in supplied:
                    values = value if isinstance(value, list) else [value]
                    for item in values:
                        if isinstance(item, str) and item not in supplied[name]:
                            if (name, item) not in seen:
                                seen.add((name, item))
                                found.append(
                                    UnusableAnswer(
                                        stage=stage, field=name, returned_id=item
                                    )
                                )
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(response)
    return found


def unsupplied(values: Iterable[str], supplied: Container[str]) -> list[str]:
    """The returned ids that were never supplied, in first-seen order.

    Order is stable rather than sorted-by-accident because it reaches the report,
    and two recorded runs over the same input must be byte-identical (M0.5).
    """
    seen: dict[str, None] = {}
    for value in values:
        if value not in supplied:
            seen.setdefault(value, None)
    return list(seen)
