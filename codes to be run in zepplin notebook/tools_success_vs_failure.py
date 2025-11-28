%spark.pyspark
from pyspark.sql.functions import *
from pyspark.sql.window import Window

# First, extract tool invocations with their names
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

# Join tool invocations with their results based on sequential order
# Assuming result comes immediately after invocation
tool_with_results = tool_invocations.join(
    tool_results,
    tool_invocations.row_id == tool_results.row_id,
    "left"
).select(
    tool_invocations.tool_name,
    tool_results.result
)

# Classify results as Success or Failure
tool_performance = tool_with_results.withColumn(
    "status",
    when(col("result").rlike(r"(?i)(ok|success)"), "Success")
    .otherwise("Failure")
).groupBy("tool_name", "status").count() \
 .orderBy("tool_name", "status")



# Calculate success rate per tool
tool_summary = tool_performance.groupBy("tool_name").pivot("status").sum("count") \
    .fillna(0) \
    .withColumn("total", col("Success") + col("Failure")) \
    .withColumn("success_rate", round((col("Success") / col("total")) * 100, 2)) \
    .orderBy(col("success_rate").desc())

print("\nTool Success Rate Summary:")
print("=" * 80)
tool_summary.show(100, truncate=False)

%spark.pyspark
import matplotlib.pyplot as plt
import numpy as np

# Convert to pandas
tool_summary_pd = tool_summary.toPandas()

# Sort by total usage
tool_summary_pd = tool_summary_pd.sort_values('total', ascending=True)

# Create figure with more width
fig, ax = plt.subplots(figsize=(14, 8))

# Get y positions
y_pos = np.arange(len(tool_summary_pd))

# Plot failures on the left (negative) and successes on the right (positive)
ax.barh(y_pos, -tool_summary_pd['Failure'], height=0.7, 
        color='#e74c3c', label='Failure', edgecolor='black', linewidth=1)
ax.barh(y_pos, tool_summary_pd['Success'], height=0.7, 
        color='#2ecc71', label='Success', edgecolor='black', linewidth=1)

# Customize
ax.set_yticks(y_pos)
ax.set_yticklabels(tool_summary_pd['tool_name'], fontsize=11)
ax.set_xlabel('Count', fontsize=12, fontweight='bold')
ax.set_title('Tool Performance: Success vs Failure Distribution', fontsize=16, fontweight='bold', pad=20)
ax.axvline(x=0, color='black', linewidth=1.5)
ax.legend(loc='lower left', fontsize=11)
ax.grid(axis='x', alpha=0.3, linestyle='--')

# Add count labels on bars
for i, (success, failure) in enumerate(zip(tool_summary_pd['Success'], tool_summary_pd['Failure'])):
    # Success label
    if success > 0:
        ax.text(success + 2, i, str(int(success)), 
                va='center', ha='left', fontsize=10, fontweight='bold')
    # Failure label
    if failure > 0:
        ax.text(-failure - 2, i, str(int(failure)), 
                va='center', ha='right', fontsize=10, fontweight='bold')

# Get the maximum success value to position percentages outside the chart
max_success = tool_summary_pd['Success'].max()

# Add success rate percentage outside the bars (further right)
for i, rate in enumerate(tool_summary_pd['success_rate']):
    ax.text(max_success + 15, i, f'{rate}%', 
            va='center', ha='left', fontsize=9, 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3))

# Extend x-axis to accommodate percentage labels
ax.set_xlim(-tool_summary_pd['Failure'].max() * 1.1, max_success + 30)

plt.tight_layout()

# Save
chart_path = '/tmp/tool_performance_tornado.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.show()

print(f"\nTornado chart saved to: {chart_path}")

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file(chart_path, 'agent-dashboard-website', 'dashboard/tools_sucess_vs_failure_rate.png')