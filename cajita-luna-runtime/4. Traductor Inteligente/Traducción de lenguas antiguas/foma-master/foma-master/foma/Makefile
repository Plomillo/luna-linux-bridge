# Generic make-based build for foma (no CMake required)

CC ?= cc
AR ?= ar
RANLIB ?= ranlib
FLEX ?= flex
BISON ?= bison
INSTALL ?= install
PKG_CONFIG ?= pkg-config

PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin
LIBDIR ?= $(PREFIX)/lib
INCLUDEDIR ?= $(PREFIX)/include
PKGCONFIGDIR ?= $(LIBDIR)/pkgconfig

UNAME_S := $(shell uname -s)
IS_WINDOWS :=
ifeq ($(OS),Windows_NT)
	IS_WINDOWS := 1
endif
ifneq (,$(findstring MINGW,$(UNAME_S)))
	IS_WINDOWS := 1
endif
ifneq (,$(findstring MSYS,$(UNAME_S)))
	IS_WINDOWS := 1
endif
ifneq (,$(findstring CYGWIN,$(UNAME_S)))
	IS_WINDOWS := 1
endif

# Pick the newest C standard this compiler accepts (fall back to C99).
CSTD ?= $(shell \
	for s in c23 c17 c11 c99; do \
		echo 'int main(void){return 0;}' | $(CC) -x c -std=$$s - -o /dev/null >/dev/null 2>&1 && { echo -std=$$s; break; }; \
	done)
ifeq ($(strip $(CSTD)),)
	CSTD := -std=c99
endif

WARN_CFLAGS ?= -Wall -Wextra -Wno-missing-field-initializers -Wno-deprecated -Wno-unused-parameter
CPPFLAGS ?=
CFLAGS ?= -O2 $(WARN_CFLAGS) $(CSTD)
LDFLAGS ?=

ZLIB_LIBS ?= -lz

# Let users override these; try pkg-config first.
READLINE_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags readline 2>/dev/null)
READLINE_LIBS ?= $(shell $(PKG_CONFIG) --libs readline 2>/dev/null)
ifeq ($(strip $(READLINE_LIBS)),)
	READLINE_LIBS = -lreadline
endif

GETOPT_LIBS ?=

ifeq ($(IS_WINDOWS),1)
	SHLIB_EXT := dll
	# Also emit an import library for downstream Windows linkers.
	SHLIB_LDFLAGS := -shared -Wl,--out-implib,libfoma.dll.a
else ifeq ($(UNAME_S),Darwin)
	SHLIB_EXT := dylib
	SHLIB_LDFLAGS := -dynamiclib -Wl,-install_name,$(LIBDIR)/libfoma.$(SHLIB_EXT)
else
	SHLIB_EXT := so
	SHLIB_LDFLAGS := -shared -Wl,-soname,libfoma.$(SHLIB_EXT)
endif

ifneq ($(IS_WINDOWS),1)
	CPPFLAGS += -D_GNU_SOURCE
	CFLAGS += -fPIC
endif

EXEEXT :=
ifeq ($(IS_WINDOWS),1)
	EXEEXT := .exe
endif

VERSION := $(shell awk '$$2=="MAJOR_VERSION"{maj=$$3} $$2=="MINOR_VERSION"{min=$$3} $$2=="BUILD_VERSION"{bld=$$3} END{print maj"."min"."bld}' fomalib.h)

OBJDIR := obj

LIB_SRCS := \
	apply.c \
	coaccessible.c \
	constructions.c \
	define.c \
	determinize.c \
	dynarray.c \
	extract.c \
	flags.c \
	int_stack.c \
	io.c \
	lexcread.c \
	mem.c \
	minimize.c \
	reverse.c \
	rewrite.c \
	sigma.c \
	spelling.c \
	stringhash.c \
	structures.c \
	topsort.c \
	trie.c \
	utf8.c \
	lex.yy.c \
	lex.lexc.c \
	lex.cmatrix.c \
	regex.c

BIN_SRCS := foma.c stack.c iface.c lex.interface.c

LIB_OBJS := $(patsubst %.c,$(OBJDIR)/%.o,$(LIB_SRCS))
BIN_OBJS := $(patsubst %.c,$(OBJDIR)/%.o,$(BIN_SRCS))

FOMA_BIN := foma$(EXEEXT)
FLOOKUP_BIN := flookup$(EXEEXT)
CGFLOOKUP_BIN := cgflookup$(EXEEXT)
ALL_BINS := $(FOMA_BIN) $(FLOOKUP_BIN) $(CGFLOOKUP_BIN)

.PHONY: all clean distclean install uninstall check

all: libfoma.a libfoma.$(SHLIB_EXT) $(ALL_BINS)

# ---- code generation (flex/bison) ----
regex.c regex.h: regex.y
	$(BISON) -d -o regex.c regex.y

lex.yy.c: regex.l regex.h
	$(FLEX) -8 -o $@ $<

lex.lexc.c: lexc.l
	$(FLEX) -8 --prefix=lexc -o $@ $<

lex.interface.c: interface.l
	$(FLEX) -8 --prefix=interface -o $@ $<

lex.cmatrix.c: cmatrix.l
	$(FLEX) -8 --prefix=cmatrix -o $@ $<

# ---- object compilation ----
$(OBJDIR):
	mkdir -p $@

$(OBJDIR)/%.o: %.c | $(OBJDIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(READLINE_CFLAGS) -c $< -o $@

# ---- libraries ----
libfoma.a: $(LIB_OBJS)
	$(AR) rcs $@ $^
	$(RANLIB) $@

libfoma.$(SHLIB_EXT): $(LIB_OBJS)
	$(CC) $(LDFLAGS) $(SHLIB_LDFLAGS) -o $@ $^ $(ZLIB_LIBS)

# ---- binaries ----
$(FOMA_BIN): $(BIN_OBJS) libfoma.a
	$(CC) $(LDFLAGS) -o $@ $(BIN_OBJS) libfoma.a $(READLINE_LIBS) $(GETOPT_LIBS) $(ZLIB_LIBS)

$(FLOOKUP_BIN): flookup.c libfoma.a
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ flookup.c libfoma.a $(GETOPT_LIBS) $(ZLIB_LIBS)

$(CGFLOOKUP_BIN): cgflookup.c libfoma.a
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ cgflookup.c libfoma.a $(GETOPT_LIBS) $(ZLIB_LIBS)

libfoma.pc:
	@printf 'prefix=%s\n' '$(PREFIX)' > $@
	@printf 'exec_prefix=%s\n' '$(PREFIX)' >> $@
	@printf 'libdir=%s\n' '$(LIBDIR)' >> $@
	@printf 'includedir=%s\n\n' '$(INCLUDEDIR)' >> $@
	@printf 'Name: foma\nDescription: The foma library\nVersion: %s\n' '$(VERSION)' >> $@
	@printf 'Cflags: -I$${includedir}\n' >> $@
	@printf 'Libs: -L$${libdir} -lfoma\n' >> $@

install: all libfoma.pc
	$(INSTALL) -d $(DESTDIR)$(BINDIR) $(DESTDIR)$(LIBDIR) $(DESTDIR)$(INCLUDEDIR) $(DESTDIR)$(PKGCONFIGDIR)
	$(INSTALL) -m 0755 $(ALL_BINS) $(DESTDIR)$(BINDIR)/
ifeq ($(IS_WINDOWS),1)
	$(INSTALL) -m 0644 libfoma.a libfoma.dll.a $(DESTDIR)$(LIBDIR)/
	$(INSTALL) -m 0755 libfoma.$(SHLIB_EXT) $(DESTDIR)$(BINDIR)/
else
	$(INSTALL) -m 0644 libfoma.a libfoma.$(SHLIB_EXT) $(DESTDIR)$(LIBDIR)/
endif
	$(INSTALL) -m 0644 fomalib.h fomalibconf.h $(DESTDIR)$(INCLUDEDIR)/
	$(INSTALL) -m 0644 libfoma.pc $(DESTDIR)$(PKGCONFIGDIR)/

uninstall:
	rm -f \
		$(DESTDIR)$(BINDIR)/$(FOMA_BIN) \
		$(DESTDIR)$(BINDIR)/$(FLOOKUP_BIN) \
		$(DESTDIR)$(BINDIR)/$(CGFLOOKUP_BIN) \
		$(DESTDIR)$(LIBDIR)/libfoma.a \
		$(DESTDIR)$(LIBDIR)/libfoma.$(SHLIB_EXT) \
		$(DESTDIR)$(LIBDIR)/libfoma.dll.a \
		$(DESTDIR)$(BINDIR)/libfoma.dll \
		$(DESTDIR)$(INCLUDEDIR)/fomalib.h \
		$(DESTDIR)$(INCLUDEDIR)/fomalibconf.h \
		$(DESTDIR)$(PKGCONFIGDIR)/libfoma.pc

clean:
	rm -rf $(OBJDIR) $(ALL_BINS) libfoma.a libfoma.$(SHLIB_EXT) libfoma.dll.a libfoma.pc

# Remove generated lexer/parser C and headers too.
distclean: clean
	rm -f regex.c regex.h lex.yy.c lex.lexc.c lex.interface.c lex.cmatrix.c regex.output

check: all
	cd tests && PATH="$(CURDIR):$$PATH" ./run.sh
