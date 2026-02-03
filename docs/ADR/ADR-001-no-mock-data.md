# ADR-001: No Mock Data in Production Code

## Status
Accepted

## Context

During the development of the TalkAI platform MVP, we relied heavily on mock data for rapid prototyping and testing. This approach allowed us to:

1. Develop features without requiring full infrastructure access
2. Create deterministic test scenarios
3. Enable frontend development to proceed in parallel with backend APIs

However, as we transition to production, mock data presents several risks:

- **Accidental deployment**: Mock data could be accidentally committed and deployed to production
- **Security concerns**: Mock data might contain patterns that resemble real infrastructure
- **Code quality**: Production code containing mock functions is confusing and unprofessional
- **Testing integrity**: Mock data mixed with production code makes it unclear what's being tested

## Decision

We will **strictly prohibit mock data in production code** with the following safeguards:

### 1. Definition of Mock Data

Mock data includes:
- Functions with `mock`, `fake`, `dummy`, or `stub` prefixes (e.g., `_get_mock_resources`, `get_mock_namespaces`)
- Variables named `mock_data`, `MOCK_DATA`, `fake_data`, etc.
- Use of `MagicMock`, `Mock`, or `@patch` in production code
- Hardcoded "test-" prefixes in resource identifiers (outside of tests)
- JSON/YAML files containing mock infrastructure definitions

### 2. Where Mock Data IS Allowed

Mock data is explicitly allowed only in:
- Test files: `test_*.py`, `*_test.py`
- Test directories: `tests/`, `test/`
- Test fixtures: `conftest.py`, `fixtures/`
- Mock data files in test directories: `tests/data/`, `tests/fixtures/`

### 3. Enforcement Mechanisms

#### Pre-Commit Hooks
All commits are scanned for mock patterns before being allowed:
```yaml
- repo: local
  hooks:
    - id: check-no-mock
      entry: python scripts/check-no-mock.py
```

#### CI/CD Pipeline
The first job in our CI pipeline runs mock detection and fails immediately if found:
```yaml
jobs:
  mock-detection:
    name: Mock Data Detection
    runs-on: ubuntu-latest
    steps:
      - name: Check for mock data
        run: python scripts/check-no-mock.py
```

#### Detection Script
`scripts/check-no-mock.py` scans for:
- Mock function names (`_get_mock_*`, `get_mock_*`)
- Mock variable names (`mock_data`, `MOCK_*`)
- Testing utilities in production (`MagicMock`, `@patch`)
- Hardcoded test prefixes (`"test-"` in strings)
- Excludes: `tests/`, `*_test.py`, `test_*.py`, `docs/`

### 4. Migration Strategy

For existing mock data in production code:

1. **Identify**: Run `scripts/check-no-mock.py` to find all instances
2. **Migrate**: Move mock functions to appropriate test files or `tests/` directories
3. **Refactor**: Replace mock data with real data sources or database fixtures
4. **Verify**: Re-run detection script until clean

### 5. Exceptions

Exceptions require:
- Explicit approval from Tech Lead
- Documentation in code comments explaining why
- Tracking issue for eventual removal
- Never allowed in production deployments

## Consequences

### Positive

1. **Production Safety**: Zero risk of accidentally deploying mock data
2. **Code Clarity**: Clear separation between production and test code
3. **Professional Quality**: Production code is clean and focused
4. **Testing Integrity**: Mock data is explicitly in tests, making test intent clear
5. **Developer Confidence**: Developers can trust that production code contains only real logic

### Negative

1. **Development Speed**: Slightly slower development without easy mock fallbacks
2. **Testing Requirements**: Requires proper test infrastructure (databases, fixtures)
3. **Migration Effort**: Existing code requires cleanup (one-time cost)
4. **CI Time**: Adds ~30-60 seconds to CI pipeline

### Mitigations

- Provide comprehensive test fixtures and factories
- Document proper testing patterns in AGENTS.md
- Offer local development Docker Compose with seeded test data
- Use `pytest` fixtures and `factory_boy` for test data generation

## Implementation

### Phase 1: Enforcement (Week 1)
- [x] Create `scripts/check-no-mock.py`
- [x] Add pre-commit hooks (`.pre-commit-config.yaml`)
- [x] Update CI/CD pipeline (`.github/workflows/ci.yml`)
- [x] Create this ADR
- [x] Update README.md with policy section

### Phase 2: Migration (Week 1-2)
- [ ] Identify all mock data in production code
- [ ] Move mock functions to appropriate test locations
- [ ] Replace with real data sources where needed
- [ ] Update AGENTS.md with testing best practices

### Phase 3: Verification (Ongoing)
- [ ] CI blocks all PRs with mock data in production
- [ ] Regular audits of codebase
- [ ] Developer training on testing patterns

## Related Documents

- [README.md](../README.md) - No Mock Data Policy section
- [AGENTS.md](../AGENTS.md) - Testing standards and patterns
- `scripts/check-no-mock.py` - Detection script
- `.pre-commit-config.yaml` - Pre-commit configuration
- `.github/workflows/ci.yml` - CI/CD configuration

## References

- [Python Testing Best Practices](https://docs.pytest.org/en/latest/explanation/goodpractices.html)
- [Pre-commit Framework](https://pre-commit.com/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**Decision Date**: 2026-02-03  
**Decision Maker**: Architecture Team  
**Last Updated**: 2026-02-03
