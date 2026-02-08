# GitSmart CLI

> AI-powered Git workflow assistant for developers.

![PyPI](https://img.shields.io/pypi/v/gitsmart)
![Python](https://img.shields.io/pypi/pyversions/gitsmart)
![License](https://img.shields.io/github/license/Alex-Stulen/gitsmart-cli)

GitSmart CLI leverages AI to streamline your Git workflow with intelligent commit messages, code reviews, and repository analytics.

## Features

✅ **AI-Powered Commit Messages** — Generate conventional commit messages from your staged changes
✅ **Smart Commit Mode** — Automatically group changes into multiple logical commits (experimental)
✅ **Code Review Assistant** — Get AI feedback on branch changes
✅ **Repository Analytics** — Insights into hotspots, contributors, and code trends
✅ **Multi-Language Support** — Commit messages in 100+ languages (ISO 639-1)
✅ **Usage Tracking** — Monitor your API usage and plan limits

## Installation

```bash
pip install gitsmart
```

## Quick Start

### 1. Configure your API key

```bash
gitsmart configure
```

You'll be prompted for:
- API key (get one at [gitsmart.io](https://gitsmart.io))
- API URL (default: https://api.example.com)
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
gitsmart commit --lang ru
```

#### 🚀 Smart Commit Mode (Experimental)

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
- Experimental feature - may need refinement

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
- Complexity assessment

### `analyze` — Repository analytics

Get AI insights into your repository:

```bash
# Analyze last 90 days
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

### `usage` — API usage stats

```bash
gitsmart usage
```

Shows:
- Requests used this month
- Requests remaining
- Plan limit
- Usage progress bar

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
| `api_url` | API endpoint URL | `https://api.example.com` |
| `commit_language` | ISO 639-1 language code | `en` |

## Language Support

Commit messages can be generated in 100+ languages using ISO 639-1 codes:

```bash
# English (default)
gitsmart commit

# Spanish
gitsmart commit --lang es

# Russian
gitsmart commit --lang ru

# Japanese
gitsmart commit --lang ja

# German
gitsmart commit --lang de

# French
gitsmart commit --lang fr
```

Set default language in config:
```bash
gitsmart config commit_language ru
```

## API Plans

| Plan | Monthly Requests | Price |
|------|-----------------|-------|
| Free | 50 | $0 |
| Basic | 1,000 | $9.99 |
| Pro | 10,000 | $29.99 |

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
# Check remaining requests
gitsmart usage

# Output:
# API Usage — 2026-02
# Plan      Free
# Period    2026-02
# Used      15 / 50
# Remaining 35
# ████████░░░░░░░░░░░░
```

## Troubleshooting

### "No API key configured"

Run `gitsmart configure` to set up your API key.

### "Not inside a git repository"

Commands like `commit`, `review`, and `analyze` must be run inside a git repository.

### "Invalid language code"

Use ISO 639-1 language codes (2 letters). Examples: `en`, `es`, `ru`, `de`, `fr`, `ja`

### "Rate limit exceeded"

You've reached your monthly request limit. Upgrade your plan at [gitsmart.io](https://gitsmart.io)

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
- 📧 Support: support@gitsmart.io

---

⭐ **Star us on GitHub** if you find GitSmart useful!
