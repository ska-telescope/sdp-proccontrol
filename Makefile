NAME := ska-sdp-proccontrol
PDIR := ska_sdp_proccontrol
VERSION := $(patsubst '%',%, $(shell awk -F' = ' '/^VERSION =/{print $$2}' src/$(PDIR)/release.py))

include make/Makefile

release-patch: ## Patch release
	bumpver update -n --tag final

release-minor: ## Minor release
	bumpver update --minor -n --tag final

release-major: ## Major release
	bumpver update --major -n --tag final

patch-beta: ## Beta patch release
	bumpver update --patch --tag beta -n