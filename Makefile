VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: setup validate test build-db export-viz build-site visualize serve all clean

setup:
	python3 -m venv $(VENV)
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
	cd build/site && python3 -m http.server 8000

visualize:
	$(PYTHON) scripts/visualize.py

all: validate build-db export-viz visualize build-site

clean:
	rm -rf build
