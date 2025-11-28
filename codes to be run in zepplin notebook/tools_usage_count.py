%pyspark
from pyspark.sql.functions import *
import json
import boto3

# Load data from S3 with multiLine option
df = spark.read.option("multiLine", "true").json("s3://agent-actions-logs/logs-insights-results-fixed.json/part-00000-d007150a-8ed7-4718-99f3-945fcb6b7795-c000.txt")

print(f"Total records loaded: {df.count()}")

# Extract tool names from "Invoking:" messages
tool_counts = df.filter(col("@message").contains("Invoking:")) \
    .withColumn("tool_name", regexp_extract(col("@message"), r'Invoking: `([^`]+)`', 1)) \
    .groupBy("tool_name").count() \
    .orderBy(col("count").desc())

print("\nTool Usage Distribution:")
print("="*80)
tool_counts.show(tool_counts.count(), truncate=False)

# Convert to pandas for JSON export
tool_counts_pd = tool_counts.toPandas()

# Create JSON structure
json_data = {
    "total_invocations": int(tool_counts_pd['count'].sum()),
    "unique_tools": len(tool_counts_pd),
    "data": [
        {"tool_name": row['tool_name'], "count": int(row['count'])} 
        for _, row in tool_counts_pd.iterrows()
    ]
}

# Save JSON locally
json_path = '/tmp/tool_usage.json'
with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)

print(f"\nJSON saved locally: {json_path}")

# Upload JSON to S3
s3 = boto3.client('s3', region_name='us-east-1')
s3.upload_file(json_path, 'agent-dashboard-website', 'dashboard/data/tool_usage.json')
print("✅ JSON uploaded to S3!")

print("\n" + "="*80)
print("✅ SCRIPT 2 COMPLETED SUCCESSFULLY!")
print("="*80)