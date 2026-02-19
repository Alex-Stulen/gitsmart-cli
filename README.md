# GitSmart CLI

> AI-powered Git workflow assistant for developers.

![PyPI](https://img.shields.io/pypi/v/gitsmart)
![Python](https://img.shields.io/pypi/pyversions/gitsmart)
![License](https://img.shields.io/github/license/Alex-Stulen/gitsmart-cli)

GitSmart CLI leverages AI to streamline your Git workflow with intelligent commit messages, code reviews, and repository analytics.

> 📖 **Full documentation:** [docs.gitsmart.io](https://docs.gitsmart.io)

## Features

✅ **AI-Powered Commit Messages** — Generate conventional commit messages from your staged changes

✅ **Smart Commit Mode** — Automatically group changes into multiple logical commits

✅ **Security Scan** — Detect real vulnerabilities before they reach your repo

✅ **Plain Language Search** — Query your commit history like asking a colleague

✅ **Code Explain** — Generate PR-ready documentation from your changes

✅ **Code Review Assistant** — Get AI feedback on branch changes

✅ **Repository Analytics** — Insights into hotspots, contributors, and code trends

✅ **Multi-Language Support** — Output in 100+ languages (ISO 639-1)

✅ **Usage Tracking** — Monitor your API credit balance and plan limits

## Installation

**Requirements:** Python 3.8+, Git on your `$PATH`, a [GitSmart account](https://gitsmart.io)

### Recommended: install in a virtual environment

```bash
# Create a virtual environment (once)
python -m venv ~/.venvs/gitsmart

# Activate it
source ~/.venvs/gitsmart/bin/activate   # macOS / Linux
# or
~\.venvs\gitsmart\Scripts\activate      # Windows

# Install GitSmart
pip install gitsmart
```

To use GitSmart without activating the venv every time, add it to your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
export PATH="$HOME/.venvs/gitsmart/bin:$PATH"
```

### Alternative: global install

```bash
pip install gitsmart
```

> **Note:** A global install may conflict with other Python packages. The virtual environment approach is cleaner, especially on macOS.

### Verify the installation

```bash
gitsmart --version
```

### Update

```bash
pip install --upgrade gitsmart
# or, if using a venv:
source ~/.venvs/gitsmart/bin/activate && pip install --upgrade gitsmart
```

### Uninstall

```bash
pip uninstall gitsmart
```

Your local config at `~/.gitsmart/` is not removed automatically — delete it manually if needed.

## Quick Start

### 1. Configure your API key

```bash
gitsmart configure
```

You'll be prompted for:
- API key (get one at [gitsmart.io](https://gitsmart.io))
- API URL (default: `https://api.gitsmart.io`)
- Commit language (default: `en`)

### 2. Generate a commit message

```bash
# Stage your changes
git add .

# Generate AI commit message
gitsmart commit
```

### 3. Review the suggestion and commit

GitSmart will analyze your changes and suggest a commit message. You can:
- Press `y` to commit
- Press `e` to edit the message
- Press `n` to abort

## Commands

### `commit` — Generate AI commit messages

```bash
# Interactive mode (default)
gitsmart commit

# Auto-commit without confirmation
gitsmart commit --auto

# Force commit type
gitsmart commit --type feat

# Detailed commit with body
gitsmart commit --detail

# Commit in another language
gitsmart commit --lang fr
```

#### 🚀 Smart Commit Mode

Automatically analyze and group staged files into multiple logical commits:

```bash
gitsmart commit --smart
```

**What it does:**
- Analyzes all staged files
- Groups related changes (e.g., tests, docs, features)
- Suggests multiple commits with separate messages
- Allows you to select which groups to commit

**Example workflow:**
```bash
# Stage multiple unrelated changes
git add src/auth.py tests/test_auth.py docs/api.md

# Let AI group them
gitsmart commit --smart

# AI suggests:
# Group 1: Authentication implementation (auth.py)
# Group 2: Authentication tests (test_auth.py)
# Group 3: API documentation (api.md)

# Choose to commit all or select specific groups
```

**Limitations:**
- Maximum 50 files

### `security` — AI security scan

Scan your code changes for real vulnerabilities before they reach the repo:

```bash
# Scan staged changes
gitsmart security --staged

# Scan a specific commit
gitsmart security --commit a3f92c1

# Scan a commit range
gitsmart security --from v1.0.0 --to HEAD

# Save report to a file
gitsmart security --staged --markdown --output SECURITY_REPORT.md
```

**What it detects:**
- SQL injection, command injection
- XSS (reflected and stored)
- Hardcoded secrets (API keys, passwords, tokens)
- Path traversal
- Insecure deserialization
- Sensitive data exposure

### `search` — Plain language commit history search

Query your commit history without regex or exact strings:

```bash
# Search by intent
gitsmart search "who last updated the authorization logic?"

# Find when a feature was introduced
gitsmart search "when was dark mode added?"

# Filter by author
gitsmart search "payment changes" --author "Ivan"

# Limit results
gitsmart search "database migrations" --limit 10
```

### `explain` — Generate PR-ready documentation

Generate a documentation-style breakdown of your changes:

```bash
# Explain staged changes
gitsmart explain --staged

# Explain a specific commit
gitsmart explain --commit a3f92c1

# Explain a commit range
gitsmart explain --from v1.0.0 --to HEAD

# Save to a Markdown file
gitsmart explain --staged --markdown --output EXPLANATION.md
```

### `review` — Code review assistant

Get AI feedback on changes between branches:

```bash
# Review current branch against main
gitsmart review

# Review specific branch
gitsmart review --branch feature/auth

# Specify base branch
gitsmart review --base develop

# Review in another language
gitsmart review --lang es
```

**What you get:**
- Summary of what changed
- Potential issues (by severity)
- Recommendations for improvement
- Verdict on overall change quality

### `analyze` — Repository analytics

Get AI insights into your repository:

```bash
# Analyze repository
gitsmart analyze

# Analysis in another language
gitsmart analyze --lang de
```

**Insights include:**
- Hotspot files (most frequently changed)
- Contributor activity patterns
- Code quality recommendations
- Language distribution

### `whoami` — Account information

```bash
gitsmart whoami
```

Shows:
- Email
- Current plan (Free/Basic/Pro)

### `usage` — Credit balance

```bash
gitsmart usage
```

Shows:
- Credits used this month
- Credits remaining
- Plan limit
- Usage progress bar

### `logs` — Usage history

```bash
# Browse recent logs
gitsmart logs

# Filter by operation type
gitsmart logs --type commit

# Show only failed operations
gitsmart logs --failed

# Show detailed info (tokens, response time)
gitsmart logs --detail
```

### `config` — Manage configuration

```bash
# View all config values
gitsmart config

# Get specific value
gitsmart config api_key

# Set a value
gitsmart config commit_language fr
```

### `logout` — Remove credentials

```bash
gitsmart logout
```

Removes your saved API key and configuration.

## Configuration

Config file location: `~/.gitsmart/config.json`

**Available settings:**

| Key | Description | Default |
|-----|-------------|---------|
| `api_key` | Your GitSmart API key | — |
| `api_url` | API endpoint URL | `https://api.gitsmart.io` |
| `commit_language` | ISO 639-1 language code | `en` |

## Language Support

Commit messages can be generated in 100+ languages using ISO 639-1 codes:

```bash
# English (default)
gitsmart commit

# Spanish
gitsmart commit --lang es

# Ukrainian
gitsmart commit --lang uk

# Japanese
gitsmart commit --lang ja

# German
gitsmart commit --lang de

# French
gitsmart commit --lang fr

...etc
```

Set default language in config:
```bash
gitsmart config commit_language fr
```

## API Plans

| Plan  | Monthly Credits | Price     | Rate Limit  |
|-------|-----------------|-----------|-------------|
| Free  | 250             | $0        | 5 req/min   |
| Basic | 5,000           | $5/month  | 20 req/min  |
| Pro   | 10,000          | $10/month | 50 req/min  |

Sign up at [gitsmart.io](https://gitsmart.io)

## Examples

### Basic workflow

```bash
# 1. Make changes
vim src/auth.py

# 2. Stage changes
git add src/auth.py

# 3. Generate commit
gitsmart commit

# AI suggests: "feat(auth): implement JWT token validation"
# Press 'y' to commit
```

### Smart commit workflow

```bash
# 1. Make multiple changes
vim src/auth.py src/users.py tests/test_auth.py

# 2. Stage all
git add .

# 3. Let AI group them
gitsmart commit --smart

# AI creates 3 logical commits:
# - feat(auth): add JWT validation
# - feat(users): update user model
# - test(auth): add JWT tests
```

### Review before merge

```bash
# Create feature branch
git checkout -b feature/new-auth

# ... make changes ...

# Review before merging
gitsmart review --base main

# Get AI feedback on:
# - Code quality issues
# - Security concerns
# - Best practice violations
```

### Track your usage

```bash
# Check remaining credits
gitsmart usage

# Output:
# Credits Usage — 2026-02
# Plan        Free
# Period      2026-02
# Used        15 / 250 credits
# Remaining   235
# ██░░░░░░░░░░░░░░░░░░
```

## Troubleshooting

### "No API key configured"

Run `gitsmart configure` to set up your API key.

### "Not inside a git repository"

Commands like `commit`, `review`, and `analyze` must be run inside a git repository.

### "Invalid language code"

Use ISO 639-1 language codes (2 letters). Examples: `en`, `es`, `uk`, `de`, `fr`, `ja`

### "Rate limit exceeded"

You've reached your monthly credit limit. Upgrade your plan at [gitsmart.io](https://gitsmart.io)

## Development

```bash
# Clone repository
git clone https://github.com/Alex-Stulen/gitsmart-cli.git
cd gitsmart-cli/cli

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e .

# Run CLI
gitsmart --help
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT © 2026 Oleksii Stulen

## Links

- 🌐 Website: [gitsmart.io](https://gitsmart.io)
- 📦 PyPI: [pypi.org/project/gitsmart](https://pypi.org/project/gitsmart)
- 🐙 GitHub: [Alex-Stulen/gitsmart-cli](https://github.com/Alex-Stulen/gitsmart-cli)
- 📧 Support: s.gitsmart@gmail.com

---

⭐ **Star us on GitHub** if you find GitSmart useful!
