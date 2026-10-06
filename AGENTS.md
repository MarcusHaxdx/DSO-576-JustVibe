# Agent workspace guidelines

## Security Guardrails

1. For vague prompts, use plan mode and wait for approval.
2. **Only touch what was asked.** Change only the files named for the task. Do
   not "improve," reformat, or refactor anything on the side. If you think
   another change is needed, propose it and wait.
3. Do not delete files or clean the repository unless explicitly prompted.
4. Do not inspect any `.docx` or `.pdf` documents unless prompted. Agent-ready information is provided in `.md` files.

## Preferences

1. Use `uv` for Python env manager. Use default global Python version if initializing.
2. Notebooks are created under `src/notebook`.
3. After you create a notebook, do not run the cells to populate the results.
4. Git is read-only for agents. Do not commit anything unless explicitly prompted. Do not init a repo if there isn't one.
5. Downloaded data should go in `data/raw`.
6. If data files are large, do not read the entire thing as an agent. Use Python to analyze them.