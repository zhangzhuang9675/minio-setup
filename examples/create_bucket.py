"""Interactive bucket creation for consoles without a create-bucket button."""
import argparse
import getpass
import ssl
from minio import Minio
import urllib3


def ensure_bucket(endpoint, access_key, secret_key, bucket, ca_file):
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key,
                   secure=True, region='us-east-1',
                   http_client=urllib3.PoolManager(
                       cert_reqs=ssl.CERT_REQUIRED, ca_certs=ca_file,
                       timeout=urllib3.Timeout(connect=5, read=15), retries=False))
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket, location='us-east-1')
    return client.bucket_exists(bucket)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--endpoint', default='127.0.0.1:9000', help='Host:port, without https://')
    parser.add_argument('--ca', required=True, help='Path to the public local CA certificate')
    parser.add_argument('--bucket', default='test')
    args = parser.parse_args()
    user = input('MinIO username / AccessKeyId: ')
    password = getpass.getpass('MinIO password / SecretAccessKey: ')
    if not ensure_bucket(args.endpoint, user, password, args.bucket, args.ca):
        raise SystemExit('Bucket verification failed')
    print('Bucket is ready:', args.bucket)
