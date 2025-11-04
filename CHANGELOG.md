# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-01-08

### Added
- Initial release of pydagu
- `DagBuilder` and `StepBuilder` for fluent DAG construction
- `DaguHttpClient` for interacting with Dagu HTTP API
- Pydantic models for type-safe DAG definitions
- HTTP executor support with retry policies
- Webhook integration patterns and examples
- Comprehensive test suite (6 HTTP tests, 95%+ coverage)
- Support for Python 3.11, 3.12, and 3.13

### Features
- Type-safe DAG creation with validation
- HTTP executor with headers, body, timeout, and retry configuration
- Automatic JSON body serialization
- Step dependencies and output capture
- Parameter and environment variable support
- Flask/Django/FastAPI webhook integration examples

### Documentation
- Complete README with quick start guide
- Webhook integration examples with WebhookManager
- Production-ready callback patterns
- GitHub Actions CI/CD workflows
