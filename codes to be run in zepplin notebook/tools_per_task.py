%pyspark
from pyspark.sql.functions import *
from pyspark.sql.window import Window
import json
import boto3
import builtins

# Load data
df = spark.read.option("multiLine", "true").json("s3://agent-actions-logs/logs-insights-results-fixed.json/part-00000-d007150a-8ed7-4718-99f3-945fcb6b7795-c000.txt")

print(f"Total records loaded: {df.count()}")

# Identify chain starts and tool invocations
events = df.filter(
    col("@message").rlike(r"(> Entering new AgentExecutor chain|Invoking:)")
).select(
    col("@timestamp"),
    col("@message")
).withColumn(
    "event_type",
    when(col("@message").contains("Entering"), "chain_start")
    .when(col("@message").contains("Invoking:"), "tool_invocation")
).orderBy("@timestamp")

# Assign chain IDs
events = events.withColumn(
    "chain_id",
    sum(when(col("event_type") == "chain_start", 1).otherwise(0)).over(
        Window.orderBy("@timestamp").rowsBetween(Window.unboundedPreceding, 0)
    )
)

# Count tools per chain
tools_per_chain = events.filter(col("event_type") == "tool_invocation") \
    .groupBy("chain_id") \
    .count() \
    .withColumnRenamed("count", "tool_count")

print("\nTools Per Chain:")
print("="*80)
tools_per_chain.orderBy("chain_id").show(100, truncate=False)

# Calculate statistics
total_chains_with_tools = tools_per_chain.count()
avg_tools = tools_per_chain.agg(avg("tool_count")).collect()[0][0]
min_tools = tools_per_chain.agg(min("tool_count")).collect()[0][0]
max_tools = tools_per_chain.agg(max("tool_count")).collect()[0][0]

# Count chains without tools
total_chains = df.filter(col("@message").contains("> Entering new AgentExecutor chain")).count()
chains_without_tools = total_chains - total_chains_with_tools

print("\n" + "="*80)
print("STATISTICS")
print("="*80)
print(f"Total Chains: {total_chains}")
print(f"Chains with Tools: {total_chains_with_tools}")
print(f"Chains without Tools: {chains_without_tools}")
print(f"Average Tools: {avg_tools:.2f}")
print(f"Min Tools: {int(min_tools)}")
print(f"Max Tools: {int(max_tools)}")
print("="*80)

# Convert to pandas
tools_per_chain_pd = tools_per_chain.toPandas()

# Create JSON - use builtins.round
json_data = {
    "total_chains": int(total_chains),
    "chains_with_tools": int(total_chains_with_tools),
    "chains_without_tools": int(chains_without_tools),
    "avg_tools": builtins.round(float(avg_tools), 2),
    "min_tools": int(min_tools),
    "max_tools": int(max_tools),
    "data": [
        {"chain_id": int(row['chain_id']), "tool_count": int(row['tool_count'])} 
        for _, row in tools_per_chain_pd.iterrows()
    ]
}

# Save JSON
json_path = '/tmp/tools_per_task.json'
with open(json_path, 'w') as f:
    json.dump(json_data, f, indent=2)

print(f"\nJSON saved: {json_path}")

# Upload to S3
s3 = boto3.client('s3', region_name='us-east-1')
s3.upload_file(json_path, 'agent-dashboard-website', 'dashboard/data/tools_per_task.json')
print("✅ JSON uploaded to S3!")
print("\n" + "="*80)
print("✅ SCRIPT 3 COMPLETED!")
print("="*80)