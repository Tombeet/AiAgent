%spark.pyspark

# Extract tool names with regex - clean and readable
tool_counts = df.filter(col("@message").contains("Invoking:")) \
    .withColumn("tool_name", regexp_extract(col("@message"), r'Invoking: `([^`]+)`', 1)) \
    .groupBy("tool_name").count() \
    .orderBy(col("count").desc())

tool_counts.show(tool_counts.count(), truncate=False)

%spark.pyspark
import matplotlib.pyplot as plt
import boto3

# Convert to pandas
tool_counts_pd = tool_counts.toPandas()

# Create figure with 2 subplots side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# Pie chart on left with labels outside
wedges, texts, autotexts = ax1.pie(tool_counts_pd['count'], 
        labels=tool_counts_pd['tool_name'], 
        autopct='%1.1f%%',
        startangle=90,
        colors=plt.cm.Set3.colors,
        pctdistance=0.85,
        labeldistance=1.1)

ax1.set_title('Agent Tool Usage Distribution', fontsize=16, fontweight='bold', pad=20)
ax1.axis('equal')

# Make percentage text bold and white
for autotext in autotexts:
    autotext.set_color('white')
    autotext.set_fontsize(10)
    autotext.set_weight('bold')

# Table on right
ax2.axis('tight')
ax2.axis('off')
table_data = tool_counts_pd.values.tolist()
table = ax2.table(cellText=table_data, 
                  colLabels=['Tool Name', 'Count'],
                  cellLoc='left',
                  loc='center',
                  colWidths=[0.6, 0.2])
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Style the header
for i in range(2):
    table[(0, i)].set_facecolor('#40466e')
    table[(0, i)].set_text_props(weight='bold', color='white')

plt.tight_layout(pad=2.0)

# Save
chart_path = '/tmp/tool_usage_combined.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.show()

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file(chart_path, 'agent-dashboard-website', 'dashboard/tool_usage_combined.png')
print("Combined chart uploaded!")