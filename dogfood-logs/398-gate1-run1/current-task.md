# Task

The `acceptance` command must find provider API keys in the `.env` file of the
directory it is run from, wherever the tool itself is installed. Today it only
finds them when it is run from inside its own source checkout: it has no `.env`
loading of its own and depends on a library that searches for `.env` next to
where that library is installed. Installed as a standalone tool and run in
another project, it sees no keys at all.

When the command starts, it loads the `.env` file in the working directory, if
there is one, before any model call. A variable already set in the environment
keeps its value; `.env` only fills in what is missing. No `.env` file is not an
error.

A missing key must be reported clearly and early, never as the provider's
"invalid API key" reply. In record mode, the command warns at startup about each
key that a model it is configured to use would need and that is not set, naming
the variable and the model. Before the first live call to a model, if that
model's key is still missing, the run stops with an error that names the
variable and the model, and the call is not sent. A run that needs no live call,
because every request is already recorded or because it runs in replay mode,
still succeeds without any keys.

## Constraints
- No model request changes, so every recorded transcript keeps replaying.

## Scope exclusions
- Reading `.env` from any directory other than the working directory.
- Keys for the coding agent that builds mutation edits.
- A command-line option to name a different `.env` file.
