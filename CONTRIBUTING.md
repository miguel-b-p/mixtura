# Contributing to Mixtura

Thank you for considering a contribution.

## How to Contribute

### Reporting Bugs & Suggestions

- Check existing issues to see if your problem or idea has already been reported.
- Open a new issue with a clear title and detailed description. For bugs, include steps to reproduce. For features, explain the benefit.

### Pull Requests

1. Fork the repository and create a feature branch from `master`.
2. Make your changes. Keep code readable and consistent with the existing Go layout.
3. Test your work with `go test ./...` from `src/`.
4. Commit with a clear message.
5. Submit a Pull Request with a summary of the behavior changed.

## Development

Mixtura is built with Go.

```bash
cd src
go test ./...
./build.sh
```

The source code lives in `src/`:

- `internal/core`: domain models, provider interface, registry, and service orchestration.
- `internal/provider/*`: package-manager backends.
- `internal/system`: command execution, cache, updates, and error normalization.
- `internal/ui`: terminal rendering, prompts, and spinner.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold it.

## License

By contributing to Mixtura, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
