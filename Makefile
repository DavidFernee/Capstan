# Capstan build. `make` bootstraps the self-hosted compiler and verifies the fixpoint.
CC      ?= cc
CFLAGS  ?= -O2 -std=gnu11 -Wall -Wno-unused-function -Wno-unused-variable -Wno-unused-but-set-variable -Wno-parentheses-equality
HARDEN_FLAGS = -fstack-protector-strong -fPIE -pie
ifeq ($(shell uname -s),Linux)
HARDEN_FLAGS += -D_FORTIFY_SOURCE=2
endif
SRC      = compiler/ast.cap compiler/lexer.cap compiler/parser.cap compiler/checker.cap compiler/ranges.cap compiler/codegen.cap compiler/main.cap
RT       = runtime/capstan_rt.h

.PHONY: all bootstrap fmt lsp test clean

all: bootstrap fmt lsp

# Stage 0 (Python) translates the compiler so it can run once.
build/stage1.py: bootstrap/capstan0.py $(SRC)
	@mkdir -p build
	python3 bootstrap/capstan0.py $@ $(SRC)

# Stage 1 (the Capstan compiler, running under Python) compiles itself to C.
build/stage2.c: build/stage1.py
	python3 build/stage1.py build -o $@ $(SRC)

build/capstanc2: build/stage2.c $(RT)
	$(CC) $(CFLAGS) $(HARDEN_FLAGS) -Iruntime $< -o $@

# Stage 2 (native) compiles itself again; the output must be identical.
build/stage3.c: build/capstanc2 $(SRC)
	./build/capstanc2 build -o $@ $(SRC)

build/capstanc: build/stage3.c $(RT)
	@cmp build/stage2.c build/stage3.c && echo "fixpoint reached: the compiler reproduces itself exactly"
	$(CC) $(CFLAGS) $(HARDEN_FLAGS) -Iruntime $< -o $@

bootstrap: build/capstanc

# The formatter, written in Capstan. Building it reports one AUDIT warning: the
# single trust() that lets it write a verified source file back.
build/capstanfmt: build/capstanc tools/fmt.cap $(RT)
	./build/capstanc build -o build/fmt.c tools/fmt.cap
	$(CC) $(CFLAGS) $(HARDEN_FLAGS) -Iruntime build/fmt.c -o $@

fmt: build/capstanfmt

# The language server, written in Capstan and built together with the compiler's front
# end so that it reports exactly what the compiler reports.
LSP_SRC  = compiler/ast.cap compiler/lexer.cap compiler/parser.cap compiler/checker.cap compiler/ranges.cap compiler/codegen.cap tools/lsp.cap
build/capstan-lsp: build/capstanc $(LSP_SRC) $(RT)
	./build/capstanc build -o build/lsp.c $(LSP_SRC)
	$(CC) $(CFLAGS) $(HARDEN_FLAGS) -Iruntime build/lsp.c -o $@

lsp: build/capstan-lsp

test: build/capstanc build/capstanfmt build/capstan-lsp
	./tests/run.sh

clean:
	rm -rf build
