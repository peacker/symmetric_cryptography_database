VENV := .venv
PYTHON := $(VENV)/bin/python
HOST_OS := $(shell uname -s)
HOST_ARCH := $(shell uname -m)

# Intel Homebrew lives in /usr/local, while Apple Silicon Homebrew lives in
# /opt/homebrew.  A migrated shell may still find the old Intel Python first,
# so prefer a native interpreter when bootstrapping the virtual environment.
ifeq ($(HOST_OS)-$(HOST_ARCH),Darwin-arm64)
BOOTSTRAP_PYTHON ?= $(shell if [ -x /opt/homebrew/bin/python3 ]; then echo /opt/homebrew/bin/python3; else echo /usr/bin/python3; fi)
else
BOOTSTRAP_PYTHON ?= python3
endif

.PHONY: setup validate test build-db export-viz build-site visualize serve all clean

setup:
	@set -e; \
	if [ -x "$(PYTHON)" ] && \
	   "$(PYTHON)" -c "import platform, sys; sys.exit(platform.machine() != '$(HOST_ARCH)')" >/dev/null 2>&1; then \
		echo "Using existing native virtual environment ($(VENV))"; \
	else \
		echo "Recreating $(VENV) with $(BOOTSTRAP_PYTHON) for $(HOST_ARCH)"; \
		rm -rf "$(VENV)"; \
		"$(BOOTSTRAP_PYTHON)" -m venv "$(VENV)"; \
	fi
	$(PYTHON) -m pip install --quiet -r requirements.txt

validate:
	$(PYTHON) scripts/validate.py

test: validate
	$(PYTHON) scripts/test_process_alignment.py

build-db:
	$(PYTHON) scripts/build_db.py

export-viz:
	$(PYTHON) scripts/export_viz.py

build-site: build-db export-viz
	$(PYTHON) scripts/build_static_site.py

serve: build-site
	cd build/site && ../../$(PYTHON) -m http.server 8000

visualize:
	$(PYTHON) scripts/visualize.py

all: validate build-db export-viz visualize build-site

clean:
	rm -rf build
