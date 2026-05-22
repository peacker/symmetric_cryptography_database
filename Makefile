VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: setup validate build-db export-viz build-site all clean

setup:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --quiet -r requirements.txt

validate:
	$(PYTHON) scripts/validate.py

build-db:
	$(PYTHON) scripts/build_db.py

export-viz:
	$(PYTHON) scripts/export_viz.py

build-site: build-db export-viz
	$(PYTHON) scripts/build_static_site.py

visualize:
	$(PYTHON) scripts/visualize.py

run-app: build-db
	$(VENV)/bin/streamlit run app/app.py

all: validate build-db export-viz visualize build-site

clean:
	rm -rf build
