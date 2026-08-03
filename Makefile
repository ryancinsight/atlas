# Atlas workspace conveniences
.PHONY: help check-mdbook-links build-mdbooks

BOOKS = repos/CFDrs/docs/book repos/helios/docs/book repos/kwavers/docs/book repos/ritk/docs/book

help:
	@echo "Atlas developer targets:"
	@echo "  make check-mdbook-links  Verify internal mdBook links across all four books"
	@echo "  make build-mdbooks       Build all four mdBooks"
	@echo "  make fmt-check           cargo fmt --check across every stack member"
	@echo "  make board-lint          Check backlog.md for duplicate item ids"

check-mdbook-links:
	python3 scripts/check_mdbook_links.py $(BOOKS)

build-mdbooks:
	set -e; \
	for book in $(BOOKS); do \
		 echo "=== building $$book ==="; \
		 (cd "$$book" && mdbook build); \
	done

fmt-check:
	@python scripts/atlas-fmt-check.py

board-lint:
	@python scripts/atlas-board-lint.py
