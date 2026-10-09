"""Loopback-only mTLS integration tests use ephemeral OpenSSL identities."""
import hashlib
import json
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import mtls_gateway as gate
import live_link
import lrb_core as base

CONTRACT=json.loads((ROOT/"CONTRACT.v0.json").read_text())


def openssl(*args):
    subprocess.run(["openssl",*map(str,args)],check=True,stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE,timeout=12)


@unittest.skipUnless(shutil.which("openssl"),"OpenSSL must be present for release")
class MTLSGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        p=Path(cls.tmp.name)
        cls.root=p
        cls.ca_key=p/"ca.key"
        cls.ca=p/"ca.pem"
        openssl("req","-x509","-newkey","rsa:2048","-nodes","-keyout",cls.ca_key,
                "-out",cls.ca,"-days","1","-subj","/CN=LRB-Test-Only-CA",
                "-addext","basicConstraints=critical,CA:TRUE",
                "-addext","keyUsage=critical,keyCertSign,cRLSign",
                "-addext","subjectKeyIdentifier=hash")
        def identity(name,ekus,san="DNS:localhost,IP:127.0.0.1"):
            key=p/(name+".key")
            req=p/(name+".csr")
            cert=p/(name+".pem")
            ext=p/(name+".ext")
            ext.write_text("basicConstraints=critical,CA:FALSE\n"
                           +"keyUsage=critical,digitalSignature,keyEncipherment\n"
                           +"subjectAltName="+san+"\n"
                           +"extendedKeyUsage="+ekus+"\n")
            openssl("req","-new","-newkey","rsa:2048","-nodes",
                    "-keyout",key,"-out",req,"-subj","/CN="+name)
            openssl("x509","-req","-in",req,"-CA",cls.ca,
                    "-CAkey",cls.ca_key,"-CAcreateserial","-out",cert,
                    "-days","1","-extfile",ext)
            key.chmod(0o600)
            return key,cert
        cls.server_key,cls.server_cert=identity("localhost","serverAuth")
        cls.client_key,cls.client_cert=identity("test-client","clientAuth")
        cls.other_key,cls.other_cert=identity("other-client","clientAuth")
        cls.bad_server_key,cls.bad_server_cert=identity("wronghost","serverAuth","DNS:wronghost")
        der=ssl.PEM_cert_to_DER_cert(cls.client_cert.read_text())
        cls.config={
            "schema":gate.SCHEMA,
            "server_cert":str(cls.server_cert),
            "server_key":str(cls.server_key),
            "client_ca":str(cls.ca),
            "client_cert_sha256":hashlib.sha256(der).hexdigest(),
            "server_cert_sha256":hashlib.sha256(cls.server_cert.read_bytes()).hexdigest(),
            "client_ca_sha256":hashlib.sha256(cls.ca.read_bytes()).hexdigest()
        }
        cls.configpath=p/"transport.json"
        cls.configpath.write_text(json.dumps(cls.config))
        cls.configpath.chmod(0o600)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.tmpstate=tempfile.TemporaryDirectory()
        self.bridge=live_link.Transport(Path(self.tmpstate.name)/"state",CONTRACT)
        config=gate.read_config(self.configpath,enforce_root=False)
        self.server=gate.Server(self.bridge,config,0,testing=True)
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmpstate.cleanup()

    def client(self,path,cert=True,other=False,method="GET"):
        c=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=str(self.ca))
        c.minimum_version=ssl.TLSVersion.TLSv1_3
        if cert:
            c.load_cert_chain(str(self.other_cert if other else self.client_cert),
                              str(self.other_key if other else self.client_key))
        raw=socket.create_connection(self.server.server_address,timeout=4)
        try:
            with c.wrap_socket(raw,server_hostname="localhost") as t:
                t.settimeout(4)
                t.sendall((method+" "+path+" HTTP/1.0\r\nHost: localhost\r\n\r\n").encode())
                data=bytearray()
                while len(data)<65536:
                    chunk=t.recv(4096)
                    if not chunk:break
                    data.extend(chunk)
                return bytes(data)
        finally:
            raw.close()

    @staticmethod
    def obj(reply):
        return json.loads(reply.split(b"\r\n\r\n",1)[1])

    def test_only_loopback_and_tls13(self):
        self.assertEqual(self.server.server_address[0],"127.0.0.1")
        self.assertIn(b"200 OK",self.client("/v1/status").split(b"\r\n",1)[0])
        self.assertFalse(self.obj(self.client("/v1/status"))["certified"])

    def test_authenticated_observation_is_not_certification(self):
        reply=self.client("/v1/observe")
        self.assertIn(b"200 OK",reply.split(b"\r\n",1)[0])
        self.assertEqual(self.obj(reply)["status"],"OBSERVED_NOT_CERTIFIED")
        self.assertGreater(len(self.bridge.ledger._records()),0)

    def test_bounded_real_tls_event_stream(self):
        response=self.client("/v1/watch?frames=2&interval_sec=1")
        self.assertIn(b"200 OK",response.split(b"\r\n",1)[0])
        body=response.split(b"\r\n\r\n",1)[1]
        frames=[json.loads(x[6:]) for x in body.split(b"\n\n") if x.startswith(b"data: ")]
        self.assertEqual([f["frame"] for f in frames],[1,2])
        self.assertFalse(frames[1]["certified"])

    def test_no_client_certificate_denied(self):
        try:
            reply=self.client("/v1/status",cert=False)
        except (ssl.SSLError, ConnectionResetError, BrokenPipeError,OSError):
            return
        self.assertNotIn(b"200 OK",reply)

    def test_other_valid_ca_client_not_pinned_is_denied(self):
        try:
            reply=self.client("/v1/status",cert=True,other=True)
        except (ssl.SSLError,ConnectionResetError,OSError):
            return
        self.assertNotIn(b"200 OK",reply)

    def test_write_http_methods_denied(self):
        self.assertIn(b"405",self.client("/v1/status",method="POST").split(b"\r\n",1)[0])

    def test_unknown_or_oversized_watch_denied(self):
        self.assertIn(b"404",self.client("/v1/sudo").split(b"\r\n",1)[0])
        reply=self.client("/v1/watch?frames=999&interval_sec=1")
        self.assertIn(b"400",reply.split(b"\r\n",1)[0])

    def test_trust_file_not_root_owned_for_real_deployment(self):
        with self.assertRaisesRegex(RuntimeError,"MTLS_KEY_OR_POLICY_OWNERSHIP_INVALID|MTLS_CONFIG_PARENT_TRUST_FAILURE"):
            gate.read_config(self.configpath,enforce_root=True)

    def test_ca_pin_mismatch_fails(self):
        wrong=dict(self.config)
        wrong["client_ca_sha256"]="a"*64
        file=Path(self.tmpstate.name)/"wrong.json"
        file.write_text(json.dumps(wrong))
        file.chmod(0o600)
        with self.assertRaisesRegex(RuntimeError,"PIN_MISMATCH"):
            gate.read_config(file,enforce_root=False)

    def test_public_binding_not_configurable(self):
        self.assertFalse(hasattr(self.server,"public_listener"))
        with self.assertRaisesRegex(RuntimeError,"LOOPBACK_PORT_INVALID"):
            gate.Server(self.bridge,self.config,443,testing=False)

    def test_rejected_clients_do_not_leak_or_double_release_slots(self):
        # Repeated authenticated-but-unpinned clients must be rejected without
        # exhausting or over-releasing the bounded concurrency semaphore.
        for _ in range(12):
            try:
                reply=self.client("/v1/status",cert=True,other=True)
                self.assertNotIn(b"200 OK",reply.split(b"\\r\\n",1)[0])
            except (ssl.SSLError,ConnectionResetError,BrokenPipeError,OSError):
                pass
        self.assertEqual(self.server.slots._value,gate.MAX_CLIENTS)
        self.assertIn(b"200 OK",self.client("/v1/status").split(b"\\r\\n",1)[0])
        self.assertEqual(self.server.slots._value,gate.MAX_CLIENTS)

    def test_client_rejects_server_certificate_with_wrong_hostname(self):
        bad=dict(self.config)
        bad["server_cert"]=str(self.bad_server_cert)
        bad["server_key"]=str(self.bad_server_key)
        bad_server=gate.Server(self.bridge,bad,0,testing=True)
        worker=threading.Thread(target=bad_server.serve_forever,daemon=True)
        worker.start()
        try:
            context=ssl.create_default_context(ssl.Purpose.SERVER_AUTH,cafile=str(self.ca))
            context.minimum_version=ssl.TLSVersion.TLSv1_3
            context.load_cert_chain(str(self.client_cert),str(self.client_key))
            raw=socket.create_connection(bad_server.server_address,timeout=4)
            try:
                with self.assertRaises(ssl.SSLCertVerificationError):
                    with context.wrap_socket(raw,server_hostname="localhost") as tls:
                        tls.sendall(b"GET /v1/status HTTP/1.0\\r\\nHost: localhost\\r\\n\\r\\n")
            finally:
                raw.close()
        finally:
            bad_server.shutdown()
            bad_server.server_close()
        self.assertEqual(self.server.slots._value,gate.MAX_CLIENTS)

if __name__=="__main__":
    unittest.main()
