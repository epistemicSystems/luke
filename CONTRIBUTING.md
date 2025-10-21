# Contributing to Insight Graph

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10 or 3.11
- Git
- (Optional) Docker for containerized development
- (Optional) Redis for distributed caching

### Local Setup

```bash
# Clone the repository
git clone https://github.com/yourorg/insight-graph.git
cd insight-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including dev dependencies)
pip install -r requirements.txt
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Initialize demo data
python scripts/init_demo_data.py

# Run tests
pytest
```

### Development Workflow

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Follow code style guidelines below
3. **Write tests**: All new code should have tests
4. **Run checks**: `make lint test`
5. **Commit**: Use conventional commits (see below)
6. **Push**: `git push origin feature/your-feature`
7. **PR**: Open a pull request with description

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use `black` for formatting: `black insight_graph/`
- Use `ruff` for linting: `ruff check insight_graph/`
- Use type hints where possible
- Maximum line length: 100 characters

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `InsightGraph`)
- **Functions/methods**: `snake_case` (e.g., `get_user`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- **Private**: Prefix with `_` (e.g., `_internal_method`)

### Example

```python
from typing import Optional
from uuid import UUID

from ..core.graph import InsightGraph
from ..core.models import User


class UserService:
    """Service for user operations."""

    def __init__(self, graph: InsightGraph):
        """
        Initialize user service.

        Args:
            graph: Insight graph instance
        """
        self.graph = graph
        self._cache: dict[UUID, User] = {}

    def get_user(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User or None if not found
        """
        if user_id in self._cache:
            return self._cache[user_id]

        user = self.graph.get_user(user_id)
        if user:
            self._cache[user_id] = user

        return user
```

## Testing

### Writing Tests

- Use `pytest` for all tests
- Put tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`

### Test Structure

```python
import pytest
from insight_graph.core.models import User

def test_user_creation():
    """Test that users can be created."""
    user = User(discord_id="123", discord_handle="TestUser")

    assert user.discord_id == "123"
    assert user.discord_handle == "TestUser"
    assert user.id is not None

@pytest.fixture
def sample_user():
    """Fixture providing a sample user."""
    return User(discord_id="456", discord_handle="FixtureUser")

def test_with_fixture(sample_user):
    """Test using a fixture."""
    assert sample_user.discord_id == "456"
```

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=insight_graph

# Specific test file
pytest tests/test_models.py

# Specific test
pytest tests/test_models.py::test_user_creation

# With verbose output
pytest -v
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### Examples

```bash
feat(personas): add controller-first console dad persona

Add new persona profile for time-constrained players who prefer
controllers and short gaming sessions.

Closes #42

---

fix(rag): correct duplicate message handling

The retriever was returning duplicate messages when threads
overlapped. Added deduplication by message ID.

Fixes #38

---

docs(api): update endpoint documentation

Add examples for all persona simulation endpoints.
```

## Pull Requests

### PR Title

Use the same format as commit messages:

```
feat(area): brief description
```

### PR Description Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing done

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)

## Related Issues
Closes #123
```

## Architecture Guidelines

### Adding New Modules

1. **Core models**: Add to `insight_graph/core/models.py`
2. **Storage**: Extend `InsightGraph` in `insight_graph/core/graph.py`
3. **Analysis**: Add to `insight_graph/understand/`
4. **Integration**: Add to `insight_graph/integrations/`
5. **API**: Add endpoints to `insight_graph/api/server.py`

### Adding Personas

1. Create YAML file in `insight_graph/personas/profiles/`
2. Follow existing persona template
3. Document pain points, goals, and impact weights
4. Add test data in `scripts/init_demo_data.py`

Example:

```yaml
id: new-persona
name: "New Persona Name"

description: |
  Detailed description of this persona's characteristics,
  hardware, and behavioral patterns.

pain_points:
  - pain.point.category

goals:
  - goal_1
  - goal_2

agent_config:
  system_prompt_template: |
    You are the "New Persona" persona...

  impact_scoring:
    weights:
      issue_type: 0.8
```

### Adding Integrations

1. Create file in `insight_graph/integrations/`
2. Implement main class with clear API
3. Add CLI test function
4. Document in `docs/RECIPES.md`

Example structure:

```python
class NewIntegration:
    """Integration with External Service."""

    def __init__(self, api_key: str):
        self.client = ExternalClient(api_key)

    def export_data(self, graph: InsightGraph) -> list[str]:
        """Export data to external service."""
        pass

    def import_data(self, graph: InsightGraph) -> list[UUID]:
        """Import data from external service."""
        pass

def main():
    """CLI test function."""
    pass

if __name__ == "__main__":
    main()
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description.

    Longer description if needed. Can span multiple lines.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty

    Example:
        >>> function_name("test", 42)
        True
    """
```

### README Updates

- Update `README.md` for major features
- Update `docs/API.md` for new APIs
- Update `docs/RECIPES.md` for new workflows
- Update `CHANGELOG.md` with changes

## Common Tasks

### Adding a New Endpoint

1. Add route in `insight_graph/api/server.py`
2. Add request/response models
3. Write tests in `tests/test_api.py`
4. Document in `docs/API.md`

### Adding Analytics

1. Create module in `insight_graph/understand/`
2. Add tests in `tests/test_understand.py`
3. Add CLI test function
4. Document in `docs/ADVANCED.md`

### Performance Optimization

1. Profile first: `python -m cProfile -o profile.stats script.py`
2. Analyze: `python -m pstats profile.stats`
3. Optimize hot paths
4. Add caching if appropriate
5. Benchmark before/after

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Creating a Release

1. Update `CHANGELOG.md`
2. Bump version in `pyproject.toml`
3. Create git tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions will:
   - Run tests
   - Build Docker image
   - Create GitHub release
   - Publish to PyPI

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/yourorg/insight-graph/discussions)
- **Bugs**: Open an [Issue](https://github.com/yourorg/insight-graph/issues)
- **Features**: Open an [Issue](https://github.com/yourorg/insight-graph/issues) with `enhancement` label
- **Chat**: Join our [Discord](https://discord.gg/yourserver)

## Code Review

All PRs require:

1. ✅ All tests passing
2. ✅ Code style checks passing
3. ✅ At least one approval
4. ✅ No merge conflicts
5. ✅ Description filled out

Reviewers will check:

- Code quality and style
- Test coverage
- Documentation
- Performance implications
- Security considerations

## Community Guidelines

- Be respectful and inclusive
- Assume good intent
- Provide constructive feedback
- Help others learn
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Insight Graph! 🎉
