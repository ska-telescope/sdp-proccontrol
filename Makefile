NAME := ska-sdp-proccontrol
VERSION := $(shell cat version.txt)

include make/Makefile

release-patch: ## Patch release
	bumpver update -n --tag final

release-minor: ## Minor release
	bumpver update --minor -n --tag final

release-major: ## Major release
	bumpver update --major -n --tag final

patch-beta: ## Beta patch release
	bumpver update --patch --tag beta -n