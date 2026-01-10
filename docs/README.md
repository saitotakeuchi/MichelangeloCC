# MichelangeloCC Documentation

## Contents

- [CLI Reference](CLI.md) - Complete command-line interface documentation
- [SKILL Guide](../README.md#using-with-claude-code) - Using MichelangeloCC with Claude Code

## Quick Links

### Commands

| Command | Documentation |
|---------|---------------|
| `mcc preview` | [Preview Commands](CLI.md#preview-commands) |
| `mcc export` | [Export Commands](CLI.md#export-commands) |
| `mcc validate` | [Validate Commands](CLI.md#validate-commands) |
| `mcc repair` | [Repair Commands](CLI.md#repair-commands) |
| `mcc info` | [Info Command](CLI.md#info-command) |
| `mcc new` | [New Command](CLI.md#new-command) |
| `mcc help` | [Help Command](CLI.md#help-command) |

### Getting Started

1. **Install**: `pip install -e .`
2. **Create project**: `mcc new my_model --template mechanical`
3. **Preview**: `mcc preview model my_model/my_model.py`
4. **Export**: `mcc export stl my_model/my_model.py -o output.stl`

### Getting Help

```bash
# General help
mcc --help
mcc help

# Command-specific help
mcc export --help
mcc export stl --help
mcc help export
```
