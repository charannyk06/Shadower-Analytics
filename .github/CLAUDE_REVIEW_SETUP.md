# Claude Code Review Setup Guide

This repository uses Claude Code Action to automatically review pull requests.

## 📋 Prerequisites

1. **Anthropic OAuth Token**: You need a Claude Code OAuth token from [Anthropic Console](https://console.anthropic.com/)

## 🔧 Setup Steps

### 1. Configure GitHub Secret

1. Go to your repository settings: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `CLAUDE_CODE_OAUTH_TOKEN`
4. Value: [paste your OAuth token from Anthropic Console]
5. Click "Add secret"

### 2. Verify Workflow Files

Ensure these files exist:
- `.github/workflows/claude-code-review.yml` - Main PR review workflow
- `.github/workflows/claude.yml` - @claude mention workflow
- `.github/prompts/claude-review-prompt.md` - Review prompt template (optional)

### 3. Test the Workflow

1. Create a test pull request
2. The workflow should automatically trigger on PR open/update
3. Check the Actions tab to see the workflow running
4. Claude will post a review comment on the PR

## 🎯 How It Works

### Automatic PR Reviews

When a pull request is:
- Opened (`opened`)
- Updated with new commits (`synchronize`)
- Reopened (`reopened`)

The workflow will:
1. Checkout the repository
2. Run Claude Code Action with a comprehensive review prompt
3. Claude analyzes the code changes
4. Claude posts a review comment directly to the PR using `gh pr comment`
5. A fallback step checks if the comment was posted and provides guidance if not

### @claude Mentions

You can also mention `@claude` in:
- PR comments
- Issue comments
- PR review comments

Claude will respond to your request interactively.

## 📝 Customization

### Filter by File Paths

Edit `.github/workflows/claude-code-review.yml`:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - "backend/**"
      - "frontend/**"
```

### Filter by PR Author

Edit `.github/workflows/claude-code-review.yml`:

```yaml
jobs:
  claude-review:
    if: |
      github.event.pull_request.user.login == 'external-contributor'
```

### Adjust Review Prompt

Edit the `prompt` section in `.github/workflows/claude-code-review.yml` to:
- Focus on specific areas (security, performance, etc.)
- Add project-specific guidelines
- Change the output format
- Adjust severity definitions

## 🔍 Troubleshooting

### Workflow Doesn't Trigger

- Check that the workflow file is in `.github/workflows/`
- Verify YAML syntax is valid
- Ensure Actions are enabled in repository settings

### "Secret Not Found" Error

- Verify `CLAUDE_CODE_OAUTH_TOKEN` is set in repository secrets
- Check the secret name matches exactly (case-sensitive)
- Ensure you're using an OAuth token, not a regular API key

### Review Comment Not Posted

- Check workflow logs for errors
- Verify `pull-requests: write` permission is set
- Ensure GitHub Actions has comment permissions enabled
- The fallback step will post a comment directing you to check logs

### Review Quality Issues

- Adjust the prompt to be more specific
- Add project-specific guidelines
- Include examples of good/bad code patterns

## 📚 Additional Resources

- [Anthropic Claude Code Action](https://github.com/anthropics/claude-code-action)
- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## ✅ Verification Checklist

After setup, verify:

- [ ] `CLAUDE_CODE_OAUTH_TOKEN` secret is configured
- [ ] Workflow triggers on PR open/update
- [ ] Review comments are posted on PRs
- [ ] Review includes structured sections (Summary, Issues, Recommendations)
- [ ] @claude mentions work in PR comments

