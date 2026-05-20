VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: setup validate build-db export-viz all clean

setup:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --quiet -r requirements.txt

validate:
	$(PYTHON) scripts/validate.py

build-db:
	$(PYTHON) scripts/build_db.py

export-viz:
	$(PYTHON) scripts/export_viz.py

visualize:
	$(PYTHON) scripts/visualize.py

run-app: build-db
	$(VENV)/bin/streamlit run app/app.py

all: validate build-db export-viz visualize

clean:
	rm -rf build
