"""One live call on openai/gpt-5.4 with a reasoning effort set (#366).

Shows the effort reached the provider — reasoning tokens reported above zero —
and that the reply parsed against its schema. Prints the usage, the controls the
provider was reported to honour, the per-stage provenance, and the parsed reply;
the raw transcript stays in a scratch store and is not committed, since it
embeds the full request.

Run with RECORD, from the repo root:
    .venv/bin/python dogfood-logs/366-gate2-live-call/live_call.py <scratch dir>
"""

import json
import sys
from pathlib import Path

from acceptance.config import RunConfig, provenance_for
from acceptance.llm import Mode, StrictResponseModel
from acceptance.usage import render, summarize

STAGE = "mutation verification: defect match"


class Answer(StrictResponseModel):
    divides_evenly: bool
    reason: str


MESSAGES = [
    {
        "role": "user",
        "content": (
            "Does 1,234,567 divide evenly by 7? Work it out, then answer with a "
            "boolean and a one-sentence reason."
        ),
    }
]


def main() -> int:
    store = Path(sys.argv[1])
    config = RunConfig(
        model="openai/gpt-5.4",
        stage_models={},
        stage_reasoning={STAGE: "low"},
        mode=Mode.RECORD,
        transcript_root=store,
    )
    client = config.build_client()
    answer = client.complete(MESSAGES, Answer, stage=STAGE)

    call = client.observed_calls[0]
    print(f"served from: {call['served_from']}")
    print(f"usage: {json.dumps(call['usage'], sort_keys=True)}")
    print(f"controls applied: {json.dumps(call['controls'], sort_keys=True)}")
    provenance = provenance_for(client)
    print(f"provenance stage_controls: {provenance.model_dump(mode='json')['stage_controls']}")
    print(f"determinism: {provenance.determinism()}")
    print(f"parsed reply: {answer.model_dump()}")
    print()
    print(render(summarize(client.observed_calls)))
    return 0 if call["usage"].get("reasoning_tokens", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
