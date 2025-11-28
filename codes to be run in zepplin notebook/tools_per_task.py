%spark.pyspark
from pyspark.sql.functions import *
from pyspark.sql.window import Window

# Identify all chain starts and tool invocations
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

# Show distribution
print("Tools Used Per Chain Execution:")
print("=" * 80)
tools_per_chain.orderBy("chain_id").show(100, truncate=False)

# Calculate statistics
total_chains_with_tools = tools_per_chain.count()
avg_tools = tools_per_chain.agg(avg("tool_count")).collect()[0][0]
min_tools = tools_per_chain.agg(min("tool_count")).collect()[0][0]
max_tools = tools_per_chain.agg(max("tool_count")).collect()[0][0]

# Count chains with NO tools (simple responses)
total_chains = df.filter(col("@message").contains("> Entering new AgentExecutor chain")).count()
chains_without_tools = total_chains - total_chains_with_tools

print("\n" + "=" * 80)
print("TOOL USAGE STATISTICS")
print("=" * 80)
print(f"Total Chains: {total_chains}")
print(f"Chains with Tools: {total_chains_with_tools}")
print(f"Chains without Tools (Direct Responses): {chains_without_tools}")
print(f"\nFor chains using tools:")
print(f"  Average Tools per Chain: {avg_tools:.2f}")
print(f"  Minimum Tools: {int(min_tools)}")
print(f"  Maximum Tools: {int(max_tools)}")
print("=" * 80)

# Distribution breakdown
print("\nTool Count Distribution:")
tools_per_chain.groupBy("tool_count") \
    .count() \
    .withColumnRenamed("count", "num_chains") \
    .orderBy("tool_count") \
    .show(50, truncate=False)

%spark.pyspark
import matplotlib.pyplot as plt
import boto3

# Convert to pandas
tools_per_chain_pd = tools_per_chain.toPandas()

# Create figure with 2 subplots side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# Scatter plot on left
scatter = ax1.scatter(tools_per_chain_pd['chain_id'], 
                      tools_per_chain_pd['tool_count'],
                      c='#3498db',  # Blue color
                      s=100,  # Size of points
                      alpha=0.6,
                      edgecolors='black',
                      linewidth=1.5)

ax1.set_title('Number of Tools Used Per Task Execution', fontsize=16, fontweight='bold', pad=20)
ax1.set_xlabel('Task ID', fontsize=12, fontweight='bold')
ax1.set_ylabel('Tool Count', fontsize=12, fontweight='bold')
ax1.grid(True, alpha=0.3, linestyle='--')
ax1.axhline(y=avg_tools, color='red', linestyle='--', linewidth=2, label=f'Average: {avg_tools:.2f}')
ax1.legend(fontsize=11)

# Table on right with statistics
ax2.axis('tight')
ax2.axis('off')

table_data = [
    ['Total Tasks', str(total_chains)],
    ['Tasks with tools usage', str(total_chains_with_tools)],
    ['Tasks without tools usage', str(chains_without_tools)],
    ['Average Tools per Task', f'{avg_tools:.2f}'],
    ['Minimum Tools usage by a task', str(int(min_tools))],
    ['Maximum Tools usage by a task', str(int(max_tools))]
]

table = ax2.table(cellText=table_data, 
                  colLabels=['Metric', 'Value'],
                  cellLoc='left',
                  loc='center',
                  colWidths=[0.7, 0.3])
table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1, 3)

# Style the header
for i in range(2):
    table[(0, i)].set_facecolor('#40466e')
    table[(0, i)].set_text_props(weight='bold', color='white')


plt.tight_layout(pad=2.0)

# Save
chart_path = '/tmp/tools_per_task_analysis.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.show()

print(f"\nChart saved to: {chart_path}")

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file(chart_path, 'agent-dashboard-website', 'dashboard/tool_per_task.png')
