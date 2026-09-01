# Atlas workspace conveniences
.PHONY: help check-mdbook-links build-mdbooks fmt-check board-lint verify-scattered-oracle search-index search-index-check search-lookup rustdoc-index rustdoc-check api-lookup output-retention

BOOKS = repos/CFDrs/docs/book repos/helios/docs/book repos/kwavers/docs/book repos/ritk/docs/book

help:
	@echo "Atlas developer targets:"
	@echo "  make check-mdbook-links  Verify internal mdBook links across all four books"
	@echo "  make build-mdbooks       Build all four mdBooks"
	@echo "  make fmt-check           cargo fmt --check across every stack member"
	@echo "  make board-lint          Check backlog.md for duplicate item ids"
	@echo "  make verify-scattered-oracle  Re-verify the ARCH-008 production split against the committed oracle"
	@echo "  make search-index        Emit SCIP symbol indexes for every stack member"
	@echo "  make search-index-check  Verify SCIP indexes are fresh for every member"
	@echo "  make search-lookup TOK=NumericLu  SCIP lookup for a symbol token"
	@echo "  make rustdoc-index       Emit rustdoc JSON API oracles (nightly, per-member selection)"
	@echo "  make rustdoc-check       Verify rustdoc oracles match their members' current HEAD"
	@echo "  make api-lookup QUERY=SparseLuSolver  rustdoc API oracle lookup"
	@echo "  make output-retention   Apply the bounded output eviction policy"

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

verify-scattered-oracle:
	@python scripts/atlas_scattered_containers_classify.py --verify-oracle scripts/oracles/arch-008-production-sites.txt

search-index:
	@python scripts/search_ladder_index.py generate

search-index-check:
	@python scripts/search_ladder_index.py check

search-lookup:
	@python scripts/search_ladder_index.py lookup $(TOK)

rustdoc-index:
	@python scripts/rustdoc_oracle.py generate

rustdoc-check:
	@python scripts/rustdoc_oracle.py check

api-lookup:
	@python scripts/rustdoc_oracle.py api $(QUERY)

output-retention:
	@python scripts/atlas-output-retention.py --apply

