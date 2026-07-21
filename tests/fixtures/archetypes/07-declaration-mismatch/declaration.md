# Builder declaration

## Mandate as understood
Provide a lookup that returns a user record by its id.

## Implementation summary
Added `get_user(users, user_id)`, which returns the matching user record.

## Test evidence
Covered the happy path: an existing id returns the expected record.

## Known limitations
Raises `KeyError` with a clear message when the id is not present.
