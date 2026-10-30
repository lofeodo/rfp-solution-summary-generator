"""Shared pytest options and fixtures."""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite golden files from the current output instead of comparing.",
    )


@pytest.fixture(scope="session")
def chunk_id() -> str:
    """A real chunk ID of Federal Way (parsed and split once per session), so stubbed
    stage outputs pass the assembler's citation check."""
    from pipeline_stubs import first_chunk_id

    return first_chunk_id()
