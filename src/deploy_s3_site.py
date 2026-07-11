"""Deploy the read-only dashboard as an S3 static website (AWS-hosted).

Only needs S3 permissions. Public read on index + public/ prefix.
Usage: python src/deploy_s3_site.py
"""
import json
import os

import boto3
from dotenv import load_dotenv

load_dotenv()
BUCKET = os.environ["S3_BUCKET"]
REGION = os.environ["AWS_REGION"]
s3 = boto3.client("s3", region_name=REGION,
                  aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
                  aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])

# allow public objects on this bucket
s3.put_public_access_block(Bucket=BUCKET, PublicAccessBlockConfiguration={
    "BlockPublicAcls": False, "IgnorePublicAcls": False,
    "BlockPublicPolicy": False, "RestrictPublicBuckets": False})

s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps({
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "PublicReadSite", "Effect": "Allow", "Principal": "*",
        "Action": "s3:GetObject",
        "Resource": [f"arn:aws:s3:::{BUCKET}/index.html",
                     f"arn:aws:s3:::{BUCKET}/public/*"]}]}))

s3.put_bucket_website(Bucket=BUCKET, WebsiteConfiguration={
    "IndexDocument": {"Suffix": "index.html"}})

html = open(os.path.join(os.path.dirname(__file__), "web",
                         "static_site.html"), "rb").read()
s3.put_object(Bucket=BUCKET, Key="index.html", Body=html,
              ContentType="text/html", CacheControl="no-cache")

url = f"http://{BUCKET}.s3-website-{REGION}.amazonaws.com/"
print("AWS-hosted dashboard:", url)
