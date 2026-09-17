"""Isolated tests: never touch the running E:\\MinIO deployment or trust store."""
from pathlib import Path
import datetime
import hashlib
import ipaddress
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import ExtendedKeyUsageOID

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / 'scripts/generate-certificates.py'


class CertificateTests(unittest.TestCase):
    def setUp(self):
        qa = REPO / '.qa'
        qa.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='cert-test-', dir=qa)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'new-install'

    def generate(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args], text=True, capture_output=True)

    def test_certificate_chain_keys_san_and_validity(self):
        result = self.generate('--lan-ip', '192.168.1.50', '--lan-ip', '192.168.1.51')
        self.assertEqual(result.returncode, 0, result.stderr)
        ca = x509.load_pem_x509_certificate((self.root/'client-certs/minio-root-ca.crt').read_bytes())
        leaf = x509.load_pem_x509_certificate((self.root/'certs/public.crt').read_bytes())
        ca.public_key().verify(leaf.signature, leaf.tbs_certificate_bytes, padding.PKCS1v15(), leaf.signature_hash_algorithm)
        ca.public_key().verify(ca.signature, ca.tbs_certificate_bytes, padding.PKCS1v15(), ca.signature_hash_algorithm)
        self.assertEqual(leaf.issuer, ca.subject)
        for cert, keyfile in [(ca,'config/https-ca-private.key'),(leaf,'certs/private.key')]:
            key = serialization.load_pem_private_key((self.root/keyfile).read_bytes(), password=None)
            self.assertEqual(cert.public_key().public_numbers(), key.public_key().public_numbers())
            self.assertEqual(key.key_size, 3072)
        self.assertTrue(ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertFalse(leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertIn(ExtendedKeyUsageOID.SERVER_AUTH, leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value)
        san = leaf.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        self.assertEqual(set(san.get_values_for_type(x509.IPAddress)), {ipaddress.ip_address(x) for x in ['127.0.0.1','::1','192.168.1.50','192.168.1.51']})
        self.assertIn('localhost', san.get_values_for_type(x509.DNSName))
        self.assertIn(socket.gethostname(), san.get_values_for_type(x509.DNSName))
        now = datetime.datetime.now(datetime.timezone.utc)
        self.assertTrue(leaf.not_valid_before_utc < now < leaf.not_valid_after_utc)
        self.assertAlmostEqual((leaf.not_valid_after_utc-now).total_seconds()/86400, 365, delta=0.01)
        self.assertEqual((self.root/'certs/CAs/minio-root-ca.crt').read_bytes(), (self.root/'client-certs/minio-root-ca.crt').read_bytes())
        self.assertEqual(json.loads((self.root/'config/https-certificate-info.json').read_text())['ipAddresses'][-1], '192.168.1.51')

    def test_repeat_run_never_replaces_existing_material(self):
        self.assertEqual(self.generate().returncode, 0)
        before = {p.relative_to(self.root):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        retry = self.generate('--lan-ip','192.168.1.50')
        self.assertNotEqual(retry.returncode,0)
        self.assertIn('refusing to overwrite', retry.stderr)
        after = {p.relative_to(self.root):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_invalid_ip_creates_no_partial_files(self):
        self.assertNotEqual(self.generate('--lan-ip','not-an-ip').returncode,0)
        self.assertFalse(self.root.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
