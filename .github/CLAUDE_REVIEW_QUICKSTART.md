# Claude Code Review - Quick Start

## 🎯 What This Does

Automatically reviews pull requests using Claude AI, checking for:

- Security vulnerabilities
- Code quality issues
- Performance problems
- Architecture adherence
- Test coverage

## ⚡ 5-Minute Setup

### 1. Get Claude OAuth Token

- Visit: https://console.anthropic.com/
- Create OAuth token for Claude Code
- Copy the token

### 2. Add GitHub Secret

- Go to: `https://github.com/YOUR_USERNAME/YOUR_REPO/settings/secrets/actions`
- Click "New repository secret"
- Name: `CLAUDE_CODE_OAUTH_TOKEN`
- Value: [paste token]
- Save

### 3. Create Workflow File

Create `.github/workflows/claude-code-review.yml`:

```yaml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  claude-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write
      id-token: write
      actions: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Run Claude Code Review
        uses: anthropics/claude-code-action@v1
        continue-on-error: true
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
          show_full_output: true
          claude_args: '--allowed-tools "Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)"'
          prompt: |
            You are an expert code reviewer. Review this pull request for:
            
            - Security vulnerabilities (SQL injection, XSS, auth bypass, exposed secrets)
            - Code quality (logic errors, edge cases, error handling)
            - Performance issues (N+1 queries, memory leaks, inefficient algorithms)
            - Architecture adherence
            - Test coverage
            
            Provide your review in this format:
            
            ### 📊 Summary
            Brief overview of the PR
            
            ### 🔴 Blocking Issues (Must Fix)
            - **`file:line`** - Issue title
              - **Reasoning**: Why this is a problem
              - **Recommendation**: How to fix
            
            ### 🟡 Important Issues (Should Fix)
            - **`file:line`** - Issue title
              - **Reasoning**: Why this matters
              - **Recommendation**: Suggested improvement
            
            ### 💡 Suggestions (Nice to Have)
            - **`file:line`** - Suggestion
              - **Reasoning**: Why this helps
              - **Recommendation**: How to implement
            
            ### ✨ Final Recommendation
            - ✅ **APPROVE** - Ready to merge
            - ⚠️ **APPROVE WITH SUGGESTIONS** - Can merge but address suggestions
            - 🔄 **REQUEST CHANGES** - Issues must be addressed
            - ❌ **BLOCK** - Critical issues prevent merge
            
            **CRITICAL**: Post your review as a comment on this PR using `gh pr comment`.
```

### 4. Test It

1. Create a test PR
2. Check Actions tab - workflow should run
3. Claude will post review comment on PR

## 🎨 Customization

### Change Review Focus

Edit the `prompt` section to focus on specific areas:

```yaml
prompt: |
  Focus on security vulnerabilities and performance issues.
  Ignore style suggestions unless they impact maintainability.
  ...
```

### Filter by File Type

Only review certain files:

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - "src/**/*.ts"
      - "src/**/*.tsx"
```

### Filter by Author

Only review PRs from external contributors:

```yaml
jobs:
  claude-review:
    if: github.event.pull_request.author_association == 'FIRST_TIME_CONTRIBUTOR'
```

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Workflow doesn't run | Check file is in `.github/workflows/` |
| "Secret not found" | Verify `CLAUDE_CODE_OAUTH_TOKEN` is set |
| No comment posted | Check workflow logs for errors |
| Review too generic | Add project-specific guidelines to prompt |

## 📖 Full Documentation

See `.github/CLAUDE_REVIEW_SETUP.md` for:
- Complete workflow with detailed prompt
- Debug workflow for troubleshooting
- @claude mention workflow
- Advanced customization options

## ✅ Done!

Your PRs will now be automatically reviewed by Claude AI! 🎉

