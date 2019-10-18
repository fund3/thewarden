import boto3
import botocore
import logging
import os

from thewarden.config import Config

ENV_BUCKET_NAME = os.getenv('ENV_BUCKET_NAME')
S3_SOURCE_FILEPATH = os.getenv('S3_SOURCE_FILEPATH')


def download_s3_file(env_bucket_name,
                     s3_source_filepath,
                     local_destination_filepath):
    s3 = boto3.resource('s3')
    try:
        s3.Bucket(env_bucket_name).download_file(s3_source_filepath,
                                                 local_destination_filepath)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            logging.error("The object does not exist.")
        else:
            raise


def download_trades_file():
    download_s3_file(env_bucket_name=ENV_BUCKET_NAME,
                     s3_source_filepath=S3_SOURCE_FILEPATH,
                     local_destination_filepath=Config.LOCAL_TRADES_PATH)
