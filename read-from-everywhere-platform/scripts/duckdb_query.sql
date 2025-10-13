INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint='http://minio:9000';
SET s3_access_key_id='minioadmin';
SET s3_secret_access_key='minioadmin';
SET s3_use_ssl=false;

SELECT source_name, COUNT(*) AS rows
FROM read_parquet('s3://processed/*/*/*/*.parquet')
GROUP BY 1;

SELECT *
FROM read_parquet('s3://processed/finance_csv/*/*.parquet')
ORDER BY transaction_ts DESC
LIMIT 5;
