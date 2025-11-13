.PHONY: run docker-build docker-run clean

run:
	PYTHONPATH=src python -m mdm_pipeline.pipeline

docker-build:
	docker build -t mdm-golden-table .

docker-run: docker-build
	docker run --rm -v $$(pwd)/artifacts:/app/artifacts mdm-golden-table

clean:
	rm -rf artifacts/* data_sources/*.csv data_sources/*.jsonl data_sources/*.xlsx data_sources/*.duckdb
