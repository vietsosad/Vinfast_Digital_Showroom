"""SQLAlchemy implementations of the domain repository protocols.

Repositories stage and flush changes but never commit; the unit of work owned
by the use case decides the transaction boundary.
"""
