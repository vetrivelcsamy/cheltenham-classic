# Entry points matching googlefonts-project-template, wired to this project's
# own build.
#
# The template's Makefile calls `gftools builder` on sources/config.yaml and
# nothing else. That cannot work here: the marks, the Latin Core expansion,
# the bowls and the kerning are all generated from measurements taken off a
# first build, so the sources have to be built once, regenerated, and built
# again. scripts/build.sh does that. sources/config.yaml is still correct and
# still present, so `gftools builder` produces the same six styles from the
# same sources for anyone who runs it -- it just has to run after build.sh.
#
#   make build   the fonts, into fonts/ and gf-submission/
#   make test    FontBakery, in the directory layout google/fonts uses
#   make images  the specimen, rendered from the built binaries
#   make venv    a virtualenv with the build requirements

FAMILY  = Libre Cheltenham
DIR     = librecheltenham
PY      = venv/bin/python3
SOURCES = $(wildcard sources/*.glyphspackage)

help:
	@echo "###"
	@echo "# Build targets for $(FAMILY)"
	@echo "###"
	@echo
	@echo "  make build:  Builds the fonts into fonts/ and gf-submission/"
	@echo "  make test:   Tests the fonts with FontBakery, under ofl/$(DIR)/"
	@echo "  make images: Renders the specimen from the built fonts"
	@echo

build: build.stamp

build.stamp: venv/touchfile sources/config.yaml $(SOURCES)
	. venv/bin/activate; ./scripts/build.sh
	touch build.stamp

venv: venv/touchfile

venv/touchfile: requirements.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/touchfile

# FontBakery reads the font's own directory for METADATA.pb and the licence,
# so the family has to be laid out the way google/fonts lays it out. Built
# outside the repository on purpose: run inside it, the check walks up and
# finds the root OFL.txt as well, and reports two licences.
test: build.stamp
	rm -rf ../.libre-cheltenham-check/ofl/$(DIR)
	mkdir -p ../.libre-cheltenham-check/ofl/$(DIR)
	cp gf-submission/*.ttf gf-submission/METADATA.pb gf-submission/OFL.txt ../.libre-cheltenham-check/ofl/$(DIR)/
	cp -r gf-submission/article ../.libre-cheltenham-check/ofl/$(DIR)/
	cd ../.libre-cheltenham-check && $(CURDIR)/venv/bin/fontbakery check-googlefonts --succinct ofl/$(DIR)/*.ttf

images: build.stamp
	. venv/bin/activate; python3 scripts/specimen.py gf-submission documentation/article/specimen.png

clean:
	rm -rf build.stamp .build-measure

.PHONY: help build venv test images clean
