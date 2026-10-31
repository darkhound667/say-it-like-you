# Taskboard

Run from the repository root with `PYTHONPATH=tools`. The default file is `TASKS.md` in the current directory. Pass `--file path/to/TASKS.md` before a subcommand to use another file.

```sh
PYTHONPATH=tools python3 -m taskboard list
PYTHONPATH=tools python3 -m taskboard list --status todo --owner codex
PYTHONPATH=tools python3 -m taskboard add "Build demo" --owner codex --branch codex/T2 --notes "API ready"
PYTHONPATH=tools python3 -m taskboard set T2 --status running --notes "Started"
PYTHONPATH=tools python3 -m taskboard next
PYTHONPATH=tools python3 -m taskboard summary
PYTHONPATH=tools python3 -m taskboard brief T2
```

`brief` copies `briefs/TEMPLATE.md` beside the selected task file into `briefs/<ID>.md` when that brief does not exist. `add` uses the first unused `T<n>` ID and starts it in `todo` status.
