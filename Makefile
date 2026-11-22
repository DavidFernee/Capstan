# Capstan build. `make` bootstraps the self-hosted compiler and verifies the fixpoint.
CC      ?= cc
CFLAGS  ?= -O2 -std=gnu11 -Wall -Wno-unused-function -Wno-unused-variable -Wno-unused-but-set-variable -Wno-parentheses-equality
SRC      = compiler/ast.cap compiler/lexer.cap compiler/parser.cap compiler/checker.cap compiler/codegen.cap compiler/main.cap
RT       = runtime/capstan_rt.h

.PHONY: all bootstrap test clean

all: bootstrap

# Stage 0 (Python) translates the compiler so it can run once.
build/stage1.py: bootstrap/capstan0.py $(SRC)
	@mkdir -p build
	python3 bootstrap/capstan0.py $@ $(SRC)

# Stage 1 (the Capstan compiler, running under Python) compiles itself to C.
build/stage2.c: build/stage1.py
	python3 build/stage1.py build -o $@ $(SRC)

build/capstanc2: build/stage2.c $(RT)
	$(CC) $(CFLAGS) -Iruntime $< -o $@

# Stage 2 (native) compiles itself again; the output must be identical.
build/stage3.c: build/capstanc2 $(SRC)
	./build/capstanc2 build -o $@ $(SRC)

build/capstanc: build/stage3.c $(RT)
	@cmp build/stage2.c build/stage3.c && echo "fixpoint reached: the compiler reproduces itself exactly"
	$(CC) $(CFLAGS) -Iruntime $< -o $@

bootstrap: build/capstanc

test: build/capstanc
	./tests/run.sh

clean:
	rm -rf build
