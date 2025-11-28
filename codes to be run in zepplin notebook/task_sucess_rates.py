%spark.pyspark
from pyspark.sql.functions import *

# Find all messages with 'status': 'success', 'message' pattern
# The pattern should match the exact format in your JSON
validation_results = df.filter(
    col("@message").rlike(r"\{'status':\s*'success',\s*'message':")
)

# If message contains NOT_VALIDATED
not_validated_count = validation_results.filter(
    col("@message").rlike(r"NOT_VALIDATED:")
).count()

# Total validations
total_validations = validation_results.count()

# Validated = total - not_validated
validated_count = total_validations - not_validated_count

print(f"Total validation attempts: {total_validations}")
print(f"Validated (Successful): {validated_count}")
print(f"Not Validated (Failed): {not_validated_count}")

# Verify they add up
print(f"\nVerification: {validated_count} + {not_validated_count} = {total_validations}")
print(f"Success Rate: {(validated_count/total_validations*100):.1f}%")

# Create summary for visualization
validation_summary = spark.createDataFrame([
    ("Validated", validated_count),
    ("Not Validated", not_validated_count)
], ["Status", "Count"])

validation_summary.show()

%spark.pyspark
import matplotlib.pyplot as plt
import boto3

# Convert to pandas
validation_summary_pd = validation_summary.toPandas()

# Calculate total
total = validation_summary_pd['Count'].sum()

# Create figure with 2 subplots side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

# Bar chart on left
bars = ax1.bar(validation_summary_pd['Status'], 
               validation_summary_pd['Count'],
               color=['#66c2a5', '#fc8d62'],  # Green for validated, orange for not validated
               edgecolor='black',
               linewidth=1.5)

ax1.set_title('Agent Task Validation Success Rate', fontsize=16, fontweight='bold', pad=20)
ax1.set_xlabel('Status', fontsize=12, fontweight='bold')
ax1.set_ylabel('Count', fontsize=12, fontweight='bold')
ax1.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on top of bars
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
            f'{int(height)}',
            ha='center', va='bottom', fontsize=14, fontweight='bold')

# Table on right - with calculated percentages
ax2.axis('tight')
ax2.axis('off')

# Create table data with actual percentage calculations
table_data = [[row['Status'], f"{(row['Count']/total*100):.2f}%"] 
              for _, row in validation_summary_pd.iterrows()]

table = ax2.table(cellText=table_data, 
                  colLabels=['Status', 'Percentage'],
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
chart_path = '/tmp/validation_success_rate.png'
plt.savefig(chart_path, dpi=150, bbox_inches='tight')
plt.show()

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file(chart_path, 'agent-dashboard-website', 'dashboard/task_success_rates.png')
print("Combined chart uploaded!")