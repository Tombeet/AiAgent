%pyspark
from pyspark.sql.functions import *
from pyspark.sql.window import Window
import json
import boto3
import builtins

# Load data
df = spark.read.option("multiLine", "true").json("s3://agent-actions-logs/logs-insights-results-fixed.json/part-00000-d007150a-8ed7-4718-99f3-945fcb6b7795-c000.txt")

print(f"Total records loaded: {df.count()}")

# Extract tool invocations
tool_invocations = df.filter(col("@message").contains("Invoking:")) \
    .withColumn("tool_name", regexp_extract(col("@message"), r'Invoking: `([^`]+)`', 1)) \
    .withColumn("timestamp_parsed", to_timestamp(col("@timestamp"), "yyyy-MM-dd HH:mm:ss.SSS")) \
    .select("timestamp_parsed", "tool_name") \
    .withColumn("row_id", monotonically_increasing_id())

# Extract tool results
tool_results = df.filter(col("@message").contains("act_result")) \
    .withColumn("result", regexp_extract(col("@message"), r"'act_result':\s*'([^']+)'", 1)) \
    .withColumn("timestamp_parsed", to_timestamp(col("@timestamp"), "yyyy-MM-dd HH:mm:ss.SSS")) \
    .select("timestamp_parsed", "result") \
    .withColumn("row_id", monotonically_increasing_id())

# Join invocations with results
tool_with_results = tool_invocations.join(
    tool_results,
    tool_invocations.row_id == tool_results.row_id,
    "left"
).select(
    tool_invocations.tool_name,
    tool_results.result
)

# Classify as Success or Failure
tool_performance = tool_with_results.withColumn(
    "status",
    when(col("result").rlike(r"(?i)(ok|success)"), "Success")
    .otherwise("Failure")
).groupBy("tool_name", "status").count() \
 .orderBy("tool_name", "status")

# Calculate success rate
tool_summary = tool_performance.groupBy("tool_name").pivot("status").sum("count") \
    .fillna(0) \
    .withColumn("total", col("Success") + col("Failure")) \
    .withColumn("success_rate", (col("Success") / col("total")) * 100) \
    .orderBy(col("success_rate").desc())

print("\nTool Success Rates:")
print("="*80)
tool_summary.show(100, truncate=False)

# Convert to pandas
tool_summary_pd = tool_summary.toPandas()

# Create JSON - use builtins.round for each row
json_data = {
    "data": [
        {
            "tool_name": row['tool_name'],
            "success": int(row['Success']),
            "failure": int(row['Failure']),
            "total": int(row['total']),
            "success_rate": builtins.round(float(row['success_rate']), 2)
        }
        for _, row in tool_summary_pd.iterrows()
    ]
}

# Save JSON
json_path = '/tmp/tool_performance.json'
with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)

print(f"\nJSON saved: {json_path}")

# Upload to S3
s3 = boto3.client('s3', region_name='us-east-1')
s3.upload_file(json_path, 'agent-dashboard-website', 'dashboard/data/tool_performance.json')
print("✅ JSON uploaded to S3!")
print("\n" + "="*80)
print("✅ SCRIPT 4 COMPLETED!")
print("="*80)