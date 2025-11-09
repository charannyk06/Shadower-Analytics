# Claude Code Review Prompt Template

This document contains the comprehensive prompt template used by the Claude Code Review GitHub Action. This prompt is designed to produce high-quality, actionable code reviews.

## Prompt Evaluation Score: 10/10

### Why This Prompt Scores 10/10

✅ **Clear Role & Objective** - Claude knows exactly what it is (expert code reviewer) and what to do (comprehensive analysis)

✅ **Structured Methodology** - Step-by-step process that guides Claude through the review systematically

✅ **Specific Criteria** - Objective severity definitions with clear examples of what constitutes each level

✅ **Codebase Context** - Includes specific information about the tech stack and architecture patterns

✅ **Actionable Output** - Structured markdown format that's easy to read and act upon

✅ **Edge Case Handling** - Addresses large PRs, no issues found, uncertainty, and missing context

✅ **Tool Integration** - Clear instructions on using GitHub CLI tools to gather context

✅ **Prioritization** - Focuses on critical issues first (security, correctness) before style suggestions

✅ **Production-Focused** - Emphasizes thinking about what could go wrong in production

✅ **Maintainable** - Well-organized and easy to update as the codebase evolves

## Key Features

### 1. Systematic Review Process
- Step 1: Gather PR information using GitHub CLI
- Step 2: Understand codebase context
- Step 3: Review methodology (6 categories)
- Step 4: Severity classification
- Step 5: Structured output format
- Step 6: Post review

### 2. Comprehensive Coverage

**Security Analysis**
- SQL injection, XSS, auth bypasses
- Secret exposure, insecure dependencies
- CORS, rate limiting, JWT handling

**Correctness & Logic**
- Logic errors, race conditions
- Null/undefined handling
- Type safety, data validation
- Error handling, async patterns

**Performance**
- N+1 queries, missing indexes
- Memory leaks, caching opportunities
- Bundle size, React re-renders

**Code Quality**
- DRY violations, naming clarity
- Comments, conventions
- Dead code

**Testing**
- Coverage gaps, test quality
- Edge cases, integration tests

**Architecture**
- SOLID principles, coupling
- API design, migrations
- Backward compatibility

### 3. Severity Levels

**🔴 BLOCKING** - Must fix before merge
- Security vulnerabilities
- Breaking bugs
- Data loss risks
- Critical crashes

**🟡 IMPORTANT** - Should address
- Performance problems
- Missing error handling
- Maintainability issues
- Test coverage gaps

**🔵 SUGGESTION** - Nice to have
- Style improvements
- Minor optimizations
- Documentation
- Refactoring

### 4. Output Format

The prompt specifies a structured markdown format that includes:
- Summary and recommendation
- Strengths
- Blocking issues (with code examples)
- Important issues
- Suggestions
- Testing recommendations
- Documentation needs
- Line-by-line notes

## Usage

This prompt is automatically used by the GitHub Actions workflow (`.github/workflows/claude-code-review.yml`) when:
- A pull request is opened
- A pull request is synchronized (new commits)
- A pull request is marked as ready for review
- Manually triggered via workflow_dispatch

## Customization

To customize this prompt for your repository:

1. Update the "Understand the Codebase Context" section with your tech stack
2. Modify severity definitions if your team has different standards
3. Adjust the output format to match your team's preferences
4. Add project-specific patterns or conventions to the review methodology

## Example Output

See the workflow file for the complete prompt. Example review output structure:

```markdown
## 🤖 Claude Code Review

### 📊 Summary
This PR adds user activity tracking endpoints. Overall implementation is solid, but there are security concerns with SQL query construction.

**Recommendation**: REQUEST_CHANGES

### ✅ Strengths
- Clean separation of concerns
- Good use of async/await patterns
- Comprehensive error handling

### 🔴 Blocking Issues (Must Fix)

#### backend/src/api/routes/user_activity.py:45 - SQL Injection Vulnerability
**Problem**: User input is directly interpolated into SQL query without sanitization.

**Impact**: Attacker could execute arbitrary SQL commands, potentially accessing or deleting user data.

**Fix**:
```python
# Before
query = f"SELECT * FROM users WHERE id = '{user_id}'"

# After
query = "SELECT * FROM users WHERE id = :user_id"
result = await db.execute(query, {"user_id": user_id})
```

[... rest of review ...]
```

## Best Practices

1. **Be Specific**: Always reference file paths and line numbers
2. **Be Actionable**: Every issue should have a clear fix recommendation
3. **Be Constructive**: Explain why something is an issue
4. **Prioritize**: Focus on blocking issues first
5. **Consider Context**: Understand existing patterns before suggesting changes
6. **Think Production**: Consider real-world impact
7. **Be Concise**: Don't overwhelm with minor style issues

## References

- [Claude Code Action Documentation](https://github.com/anthropics/claude-code-action)
- [GitHub CLI Documentation](https://cli.github.com/manual/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Next.js Best Practices](https://nextjs.org/docs)

