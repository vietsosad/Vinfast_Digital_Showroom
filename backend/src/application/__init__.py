"""Application layer: use cases that orchestrate domain rules and repositories.

Each use case receives a UnitOfWork and commits at most once, so all of its
writes succeed or fail together. Like the domain, this package must not import
FastAPI, SQLAlchemy or the API/infrastructure packages.
"""
