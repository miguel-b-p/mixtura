.PHONY: build test check clean

build:
	cd src && ./build.sh

test:
	cd src && go test ./...

check: test build

clean:
	rm -rf dist coverage.out
