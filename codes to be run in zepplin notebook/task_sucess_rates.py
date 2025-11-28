%pyspark
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import boto3
import builtins

# Load data from S3 with multiLine option
df = spark.read.option("multiLine", "true").json("s3://agent-actions-logs/logs-insights-results-fixed.json/part-00000-d007150a-8ed7-4718-99f3-945fcb6b7795-c000.txt")

print(f"Total records loaded: {df.count()}")

# Find validation results
validation_results = df.filter(
    col("@message").rlike(r"\{'status':\s*'success',\s*'message':")
)

# Count failures
not_validated_count = validation_results.filter(
    col("@message").rlike(r"NOT_VALIDATED:")
).count()

# Calculate metrics
total_validations = validation_results.count()
validated_count = total_validations - not_validated_count

print(f"\nTotal validation attempts: {total_validations}")
print(f"Validated (Successful): {validated_count}")
print(f"Not Validated (Failed): {not_validated_count}")
print(f"Success Rate: {(validated_count/total_validations*100):.1f}%")

# Create summary
validation_summary = spark.createDataFrame([
    ("Validated", validated_count),
    ("Not Validated", not_validated_count)
], ["Status", "Count"])

validation_summary.show()

# Convert to pandas
validation_summary_pd = validation_summary.toPandas()

# Create JSON - use builtins.round
json_data = {
    "total_validations": int(total_validations),
    "validated_count": int(validated_count),
    "not_validated_count": int(not_validated_count),
    "success_rate": builtins.round((validated_count/total_validations*100), 2),
    "data": [
        {"status": row['Status'], "count": int(row['Count'])} 
        for _, row in validation_summary_pd.iterrows()
    ]
}

# Save JSON
json_path = '/tmp/task_success_rates.json'
with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)

print(f"\nJSON saved: {json_path}")

# Upload to S3
s3 = boto3.client('s3', region_name='us-east-1')
s3.upload_file(json_path, 'agent-dashboard-website', 'dashboard/data/task_success_rates.json')
print("✅ JSON uploaded to S3!")
print("\n" + "="*80)
print("✅ SCRIPT 1 COMPLETED!")
print("="*80)