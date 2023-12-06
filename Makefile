.PHONY: all check test

all: check test

check:
	yapf -i -r .
	mypy -p src

test:
	llvm-lit test -sv
