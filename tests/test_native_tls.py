"""Optional isolated native MinIO HTTPS/S3/restart smoke test.

Set MINIO_TEST_EXE to an existing trusted minio.exe. Uses temporary data,
random credentials and loopback ports; never imports the user's real credentials.
"""
import datetime
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid

REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('MINIO_TEST_EXE'), 'Set MINIO_TEST_EXE for the optional native integration test')
class NativeTlsTests(unittest.TestCase):
    def test_https_s3_and_persistence_with_generated_certificate(self):
        qa = REPO / '.qa'
        qa.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='native-test-',dir=qa) as name:
            root = Path(name)
            for folder in ['data','logs','tmp']:
                (root/folder).mkdir()
            generation = subprocess.run([sys.executable,str(REPO/'scripts/generate-certificates.py'),'--root',str(root)],capture_output=True,text=True)
            self.assertEqual(generation.returncode,0,generation.stderr)
            executable = root/'minio.exe'
            shutil.copy2(os.environ['MINIO_TEST_EXE'],executable)
            def free_port():
                with socket.socket() as s:
                    s.bind(('127.0.0.1',0))
                    return s.getsockname()[1]
            api_port = free_port()
            console_port = free_port()
            while console_port == api_port:
                console_port = free_port()
            host = f'127.0.0.1:{api_port}'
            endpoint = 'https://' + host
            username, password = 'isolated-test-admin', uuid.uuid4().hex
            env = {k:v for k,v in os.environ.items() if not k.startswith('MINIO_')}
            env.update(MINIO_ROOT_USER=username,MINIO_ROOT_PASSWORD=password,MINIO_BROWSER_REDIRECT_URL=f'https://127.0.0.1:{console_port}',MINIO_UPDATE='off',TEMP=str(root/'tmp'),TMP=str(root/'tmp'))
            tls = ssl.create_default_context(cafile=str(root/'client-certs/minio-root-ca.crt'))
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=tls))
            def signed(method,path,payload=b''):
                now = datetime.datetime.now(datetime.timezone.utc)
                stamp, day = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
                digest = hashlib.sha256(payload).hexdigest()
                headers = {'host':host,'x-amz-content-sha256':digest,'x-amz-date':stamp}
                names = ';'.join(sorted(headers))
                canonical = '\n'.join([method,path,'',''.join(f'{k}:{headers[k]}\n' for k in sorted(headers)),names,digest])
                scope = f'{day}/us-east-1/s3/aws4_request'
                string = '\n'.join(['AWS4-HMAC-SHA256',stamp,scope,hashlib.sha256(canonical.encode()).hexdigest()])
                key = ('AWS4'+password).encode()
                for part in [day,'us-east-1','s3','aws4_request']:
                    key = hmac.new(key,part.encode(),hashlib.sha256).digest()
                signature = hmac.new(key,string.encode(),hashlib.sha256).hexdigest()
                headers['Authorization'] = f'AWS4-HMAC-SHA256 Credential={username}/{scope}, SignedHeaders={names}, Signature={signature}'
                req = urllib.request.Request(endpoint+path,method=method,headers=headers,data=payload if method=='PUT' else None)
                with opener.open(req,timeout=10) as response:
                    return response.read()
            args = [str(executable),'server',str(root/'data'),'--address',host,'--console-address',f'127.0.0.1:{console_port}','--certs-dir',str(root/'certs')]
            payload = b'isolated TLS persistence test ' + uuid.uuid4().hex.encode()
            bucket = '/isolated-verification'
            with (root/'logs/server.log').open('wb') as log:
                for cycle in range(2):
                    process = subprocess.Popen(args,cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
                    try:
                        ready = False
                        for _ in range(60):
                            if process.poll() is not None:
                                self.fail('Isolated MinIO exited before readiness')
                            try:
                                with opener.open(endpoint+'/minio/health/ready',timeout=1) as response:
                                    ready = response.status == 200
                                with opener.open(f'https://127.0.0.1:{console_port}',timeout=1) as response:
                                    ready = ready and response.status == 200
                                if ready:
                                    break
                            except (OSError,urllib.error.URLError):
                                ready = False
                                time.sleep(0.25)
                        self.assertTrue(ready,'Isolated MinIO did not become ready')
                        with opener.open(f'https://127.0.0.1:{console_port}',timeout=5) as response:
                            self.assertEqual(response.status,200)
                        if cycle == 0:
                            spec = importlib.util.spec_from_file_location('create_bucket', REPO/'examples/create_bucket.py')
                            helper = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(helper)
                            self.assertTrue(helper.ensure_bucket(host, username, password, bucket[1:], str(root/'client-certs/minio-root-ca.crt')))
                            self.assertTrue(helper.ensure_bucket(host, username, password, bucket[1:], str(root/'client-certs/minio-root-ca.crt')))
                            signed('PUT',bucket+'/roundtrip.txt',payload)
                            self.assertIn(b'isolated-verification',signed('GET','/'))
                        self.assertEqual(signed('GET',bucket+'/roundtrip.txt'),payload)
                        if cycle == 1:
                            signed('DELETE',bucket+'/roundtrip.txt')
                            signed('DELETE',bucket)
                    finally:
                        if process.poll() is None:
                            process.terminate()
                        process.wait(timeout=20)


if __name__ == '__main__':
    unittest.main(verbosity=2)
