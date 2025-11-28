# PROJECT PART 2 (BIG DATA TECHNOLOGY)

1. This is an orphan branch in the repo created for the purpose of agent logs analyis using big data technology (spark + aws EMR)


2. This branch contains:

- pyspark codes used to run in zepplin notebook in the AWS EMR cluster to generate data charts and reports

- index.html file which is used to present our generated charts/reports in the form of a dashboard/website


ARCHITECTURE:
1. Exported AI agent log files (showing agent's action and decision) from cloudwatch logs to S3 bucket

2. Provisioned an EMR cluster in AWS (with zepplin notebook enabled)

3. Run the pyspark codes in this branch using the EMR cluster (via zepplin note book)
(Codes in this branch runs a mini ETL pipeline which extracts ai agent logs from s3, cleans it and generate charts/reports, and load generated asset to another s3 bucket)

4. Created a html file to present the data/reports in a dashboard view

5. Hosted the html file(website) using a s3 bucket with web hosting enabled