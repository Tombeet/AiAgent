%spark.pyspark

from pyspark.sql.functions import *

# Now read it properly as JSON
df = spark.read.option("multiline", "true").json("s3://agent-actions-logs/logs-insights-results-fixed.json")



%spark.pyspark

# List of patterns to filter out (useless logs)
noise_patterns = [
    "POST /api/run_agent HTTP/1.1",
    "GET /openapi.json HTTP/1.1",
    "GET /api/screenshots",
    "Started server process",
    "Waiting for application startup",
    "Application startup complete",
    "Uvicorn running on",
    "LangChainDeprecationWarning",
    "memory=ConversationBufferMemory"
]

# Create filter condition to exclude all noise patterns
filter_condition = ~col("@message").contains(noise_patterns[0])
for pattern in noise_patterns[1:]:
    filter_condition = filter_condition & ~col("@message").contains(pattern)

# Apply filter to clean the data
df_cleaned = df.filter(filter_condition)


# Preview cleaned data
df_cleaned.show(50, truncate=False)