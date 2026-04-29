# 🤖 AI Agent Guidelines

This document outlines the core principles and operational standards for AI agents working on the Channel Transcript Archiver project.

## 🎯 Prime Directive
**Be Agentic and Autonomous.**
- **Initiative**: Take ownership of the task. If there are obvious next steps, perform them without waiting for explicit permission.
- **Quality over Speed**: Do things the "proper way" rather than the "fast way." We prioritize a "Good and Performant" solution over a cheap or rushed one.
- **Thoroughness**: Use your large context window and budget to stress test implementations. Don't be afraid to process large files or run extensive verification.

## 🛡️ Safety & Reversibility
Never perform actions that lead to irreversible data loss.
- **Safe**: Committing code, creating temporary files, clearing build caches, deleting files that can be easily re-downloaded from original sources.
- **Unsafe**: Deleting unrelated documents, clearing databases without backups, or modifying the environment in ways that cannot be undone.

## 🧪 Verification Standards
**You are not done until you have verified your work.**
- **Scale**: Test with real data at sizes the program will actually process. Mini dummy files are for initial logic only.
- **Contexts**: Verify in both interactive and non-interactive terminal contexts.
- **Zero Regressions**: Ensure new features don't break existing workflows.

## 📜 Script Design & Tooling
- **Visibility**: Use `tqdm` progress bars for interactive mode. For non-interactive logs, provide updates every 30-60 seconds to remain token-efficient while showing progress.
- **Logging**: Always use standard logging libraries with timestamps and appropriate log levels.
- **Modern Standards**: Adhere to `pyproject.toml` and best practices like `uv` for dependency management and `ruff`/`mypy` for code quality.
- **Utility**: Create helper scripts or tools to make complex tasks more legible and efficient.