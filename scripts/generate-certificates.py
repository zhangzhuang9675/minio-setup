from pathlib import Path
import argparse
import datetime
import ipaddress
import json
import socket
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

parser = argparse.ArgumentParser(description='Create a private CA and native MinIO TLS certificate; never overwrites existing certificates.')
parser.add_argument('--root', required=True, type=Path, help='Installation directory, e.g. E:\\MinIO')
parser.add_argument('--lan-ip', action='append', default=[], help='Current LAN IP; repeat for multiple addresses')
args = parser.parse_args()
root = args.root.resolve()
ip_addresses = list(dict.fromkeys(['127.0.0.1', '::1'] + [str(ipaddress.ip_address(value)) for value in args.lan_ip]))
outputs = [root / 'config/https-ca-private.key', root / 'certs/private.key', root / 'certs/public.crt', root / 'client-certs/minio-root-ca.crt', root / 'certs/CAs/minio-root-ca.crt', root / 'config/https-certificate-info.json']
if any(p.exists() for p in outputs):
    raise SystemExit('Existing certificate material found; refusing to overwrite.')
for path in outputs:
    path.parent.mkdir(parents=True, exist_ok=True)
(root / 'certs/CAs').mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.timezone.utc)
ca_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'MinIO E Local Root CA ' + now.strftime('%Y%m%d'))])
ca_cert = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
    .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(minutes=10)).not_valid_after(now + datetime.timedelta(days=3650))
    .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
    .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
    .sign(ca_key, hashes.SHA256()))
server_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
dns_names = ['localhost', socket.gethostname()]
server_cert = (x509.CertificateBuilder()
    .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'MinIO E HTTPS')]))
    .issuer_name(ca_name).public_key(server_key.public_key()).serial_number(x509.random_serial_number())
    .not_valid_before(now - datetime.timedelta(minutes=10)).not_valid_after(now + datetime.timedelta(days=365))
    .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    .add_extension(x509.SubjectAlternativeName([x509.DNSName(n) for n in dns_names] + [x509.IPAddress(ipaddress.ip_address(ip)) for ip in ip_addresses]), critical=False)
    .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
    .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
    .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
    .sign(ca_key, hashes.SHA256()))
pem = serialization.Encoding.PEM
key_format = serialization.PrivateFormat.PKCS8
(root / 'config/https-ca-private.key').write_bytes(ca_key.private_bytes(pem, key_format, serialization.NoEncryption()))
(root / 'certs/private.key').write_bytes(server_key.private_bytes(pem, key_format, serialization.NoEncryption()))
(root / 'certs/public.crt').write_bytes(server_cert.public_bytes(pem))
ca_pem = ca_cert.public_bytes(pem)
(root / 'client-certs/minio-root-ca.crt').write_bytes(ca_pem)
(root / 'certs/CAs/minio-root-ca.crt').write_bytes(ca_pem)
metadata = {'issuedAt': now.isoformat(), 'serverExpires': server_cert.not_valid_after_utc.isoformat(), 'dnsNames': dns_names, 'ipAddresses': ip_addresses, 'caSHA256': ca_cert.fingerprint(hashes.SHA256()).hex(), 'serverSHA256': server_cert.fingerprint(hashes.SHA256()).hex(), 'issuerType': 'private local CA', 'api': 'https://127.0.0.1:9000', 'console': 'https://127.0.0.1:9001'}
(root / 'config/https-certificate-info.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps(metadata, indent=2))
