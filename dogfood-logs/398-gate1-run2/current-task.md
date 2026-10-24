# Task

Wherever the `acceptance` tool is installed, when the command starts it loads
the `.env` file in the working directory, if there is one, before any model
call. Today the tool has no `.env` loading of its own, so installed as a
standalone tool and run in another project it sees no API keys at all. A
variable already set in the environment keeps its value; `.env` only fills in
what is missing. No `.env` file is not an error.

In record mode, the command warns at startup about each key that a model it is
configured to use would need and that is not set, naming the variable and the
model. Before the first live call to a model, if that model's key is still
missing, the run stops with an error that names the variable and the model, and
the call is not sent, so the user never sees the provider's "invalid API key"
reply instead. A run that needs no live call, because every request is already
recorded or because it runs in replay mode, still succeeds without any keys.

## Constraints
- No model request changes, so every recorded transcript keeps replaying.

## Scope exclusions
- Reading `.env` from any directory other than the working directory.
- Checking for keys that the coding agent which builds mutation edits needs.
- A command-line option to name a different `.env` file.
