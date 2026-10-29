.PHONY: setup install status check update-hooks

setup:
	uvx prek install

install:
	uv run sync.py install

status:
	uv run sync.py status

check:
	uvx prek run --all-files

update-hooks:
	uvx prek update --cooldown-days 7
