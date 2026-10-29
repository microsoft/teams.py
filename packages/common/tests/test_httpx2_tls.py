"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import hashlib
import ipaddress
import os
import ssl
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx2
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from microsoft_teams.common.http import Client


@dataclass
class Authority:
    key: rsa.RSAPrivateKey
    cert: x509.Certificate
    path: Path

    def directory(self) -> Path:
        directory = self.path.with_suffix(".d")
        directory.mkdir(exist_ok=True)
        # These short, lowercase UTF8 names are already OpenSSL-canonical.
        canonical_name = self.cert.subject.public_bytes()[2:]
        name_hash = int.from_bytes(hashlib.sha1(canonical_name).digest()[:4], "little")
        (directory / f"{name_hash:08x}.0").write_bytes(self.path.read_bytes())
        return directory

    def server_context(self, *, hostname: str = "localhost", expired: bool = False) -> ssl.SSLContext:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)]))
            .issuer_name(self.cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(now - timedelta(days=1) if expired else now + timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(self.key.public_key()), critical=False)
            .add_extension(
                x509.SubjectAlternativeName(
                    [x509.DNSName(hostname)]
                    + ([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))] if hostname == "localhost" else [])
                ),
                critical=False,
            )
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .sign(self.key, hashes.SHA256())
        )
        cert_path = self.path.parent / f"{cert.serial_number}.pem"
        key_path = cert_path.with_suffix(".key")
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        return context


def make_authority(path: Path, name: str) -> Authority:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=2))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return Authority(key, cert, path)


@pytest.fixture
def authorities(tmp_path: Path) -> tuple[Authority, Authority]:
    return make_authority(tmp_path / "ca.pem", "teams test ca"), make_authority(tmp_path / "other.pem", "other ca")


@pytest.fixture(autouse=True)
def isolated_tls_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in os.environ:
        if name.lower().endswith("_proxy") or name in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
            monkeypatch.delenv(name)


Handler = Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]


@asynccontextmanager
async def listen(handler: Handler, context: ssl.SSLContext | None = None) -> AsyncIterator[int]:
    tasks: list[asyncio.Task[None]] = []

    async def connected(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            with suppress(ConnectionError, asyncio.IncompleteReadError):
                await handler(reader, writer)
        finally:
            writer.close()
            with suppress(ConnectionError):
                await writer.wait_closed()

    server = await asyncio.start_server(
        lambda r, w: tasks.append(asyncio.create_task(connected(r, w))),
        "127.0.0.1",
        0,
        ssl=context,
    )
    try:
        yield server.sockets[0].getsockname()[1]
    finally:
        server.close()
        await server.wait_closed()
        for task in tasks:
            if not task.done():
                task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert all(result is None or isinstance(result, asyncio.CancelledError) for result in results), results


async def respond(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    await reader.readuntil(b"\r\n\r\n")
    writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
    await writer.drain()


@asynccontextmanager
async def tunnel(origin_port: int, context: ssl.SSLContext | None = None) -> AsyncIterator[tuple[int, list[bytes]]]:
    requests: list[bytes] = []

    async def relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()

    async def connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request = await reader.readuntil(b"\r\n\r\n")
        requests.append(request)
        assert request.startswith(f"CONNECT 127.0.0.1:{origin_port} HTTP/1.1\r\n".encode())
        upstream_reader, upstream_writer = await asyncio.open_connection("127.0.0.1", origin_port)
        try:
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            pipes = [
                asyncio.create_task(relay(reader, upstream_writer)),
                asyncio.create_task(relay(upstream_reader, writer)),
            ]
            try:
                done, _ = await asyncio.wait(pipes, return_when=asyncio.FIRST_COMPLETED)
                for task in done:
                    task.result()
            finally:
                for task in pipes:
                    task.cancel()
                await asyncio.gather(*pipes, return_exceptions=True)
        finally:
            upstream_writer.close()
            with suppress(ConnectionError):
                await upstream_writer.wait_closed()

    async with listen(connect, context) as port:
        yield port, requests


@pytest.mark.parametrize(
    ("setting", "accepted"),
    [
        ("file", True),
        ("directory", True),
        ("file_wins", True),
        ("wrong_file_wins", False),
        ("empty_file", True),
        ("empty", False),
        ("absent", False),
        ("missing_directory", False),
        ("malformed_directory", False),
    ],
)
async def test_native_ca_selection_over_real_https(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch, setting: str, accepted: bool
):
    ca, other = authorities
    if setting in ("file", "file_wins"):
        monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    if setting == "file_wins":
        monkeypatch.setenv("SSL_CERT_DIR", str(other.directory()))
    if setting == "wrong_file_wins":
        monkeypatch.setenv("SSL_CERT_FILE", str(other.path))
    if setting in ("directory", "wrong_file_wins", "empty_file"):
        monkeypatch.setenv("SSL_CERT_DIR", str(ca.directory()))
    if setting in ("empty", "empty_file"):
        monkeypatch.setenv("SSL_CERT_FILE", "")
    if setting == "empty":
        monkeypatch.setenv("SSL_CERT_DIR", "")
    if setting in ("missing_directory", "malformed_directory"):
        directory = ca.path.parent / "invalid.d"
        if setting == "malformed_directory":
            directory.mkdir()
            for certificate in ca.directory().iterdir():
                (directory / certificate.name).write_text("not a certificate", encoding="utf-8")
        monkeypatch.setenv("SSL_CERT_DIR", str(directory))

    async with listen(respond, ca.server_context()) as port:
        with patch("microsoft_teams.common.http.client.httpx2.AsyncClient", wraps=httpx2.AsyncClient) as constructor:
            client = Client()
            constructor.assert_called_once_with(base_url="", headers={}, timeout=None)
        try:
            if accepted:
                response = await client.get(f"https://127.0.0.1:{port}")
                assert isinstance(response, httpx2.Response)
                assert response.text == "ok"
            else:
                with pytest.raises(httpx2.ConnectError, match="(?i)certificate"):
                    await client.get(f"https://127.0.0.1:{port}")
        finally:
            await client.http.aclose()


@pytest.mark.parametrize("failure", ["expired", "wrong_host"])
async def test_rejects_invalid_server_certificate(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch, failure: str
):
    ca, _ = authorities
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    context = ca.server_context(
        hostname="wrong.test" if failure == "wrong_host" else "localhost", expired=failure == "expired"
    )
    async with listen(respond, context) as port:
        client = Client()
        try:
            with pytest.raises(httpx2.ConnectError, match="expired" if failure == "expired" else "IP address mismatch"):
                await client.get(f"https://127.0.0.1:{port}")
        finally:
            await client.http.aclose()


@pytest.mark.parametrize("malformed", [False, True])
def test_invalid_ca_file_fails_at_construction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, malformed: bool):
    path = tmp_path / "invalid.pem"
    if malformed:
        path.write_text("not a certificate", encoding="utf-8")
    monkeypatch.setenv("SSL_CERT_FILE", str(path))
    with pytest.raises(ssl.SSLError if malformed else FileNotFoundError):
        Client()


async def test_unreadable_ca_file_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "unreadable.pem"
    path.write_text("not readable", encoding="utf-8")
    path.chmod(0)
    try:
        try:
            path.read_bytes()
        except PermissionError:
            pass
        else:
            pytest.skip("This runner does not enforce file permission bits")
        monkeypatch.setenv("SSL_CERT_FILE", str(path))
        with pytest.raises(PermissionError):
            Client()
    finally:
        path.chmod(0o600)


async def test_injected_client_and_shared_clone_ignore_invalid_ambient_ca(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch
):
    ca, _ = authorities
    context = ssl.create_default_context(cafile=ca.path)
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path.parent / "missing.pem"))
    async with listen(respond, ca.server_context()) as port:
        async with httpx2.AsyncClient(verify=context, trust_env=False) as raw:
            client = Client(_http=raw)
            shared = client.clone(share_http=True)
            assert shared.http is raw
            assert raw.timeout == httpx2.Timeout(5)
            assert (await shared.get(f"https://127.0.0.1:{port}")).text == "ok"
            with pytest.raises(FileNotFoundError):
                client.clone()
            assert not raw.is_closed


async def test_nonsharing_clone_reevaluates_environment(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch
):
    ca, other = authorities
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    client = Client()
    monkeypatch.setenv("SSL_CERT_FILE", str(other.path))
    clone = client.clone()
    try:
        async with listen(respond, ca.server_context()) as port:
            assert (await client.get(f"https://127.0.0.1:{port}")).text == "ok"
            with pytest.raises(httpx2.ConnectError, match="(?i)certificate"):
                await clone.get(f"https://127.0.0.1:{port}")
    finally:
        await clone.http.aclose()
        await client.http.aclose()


@pytest.mark.parametrize("proxy_variable", ["HTTPS_PROXY", "ALL_PROXY"])
@pytest.mark.parametrize("bypass", [False, True])
async def test_environment_connect_proxy_and_no_proxy(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch, proxy_variable: str, bypass: bool
):
    ca, _ = authorities
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    async with listen(respond, ca.server_context()) as origin:
        async with tunnel(origin) as (proxy, requests):
            monkeypatch.setenv(proxy_variable, f"http://user:password@127.0.0.1:{proxy}")
            if bypass:
                monkeypatch.setenv("NO_PROXY", "127.0.0.1")
            client = Client()
            try:
                assert (await client.get(f"https://127.0.0.1:{origin}")).text == "ok"
                assert len(requests) == (0 if bypass else 1)
                if requests:
                    assert b"Proxy-Authorization: Basic dXNlcjpwYXNzd29yZA==" in requests[0]
            finally:
                await client.http.aclose()


async def test_http_proxy_does_not_route_https(
    authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch
):
    ca, _ = authorities
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    async with listen(respond, ca.server_context()) as origin:
        async with tunnel(origin) as (proxy, requests):
            monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{proxy}")
            client = Client()
            try:
                assert (await client.get(f"https://127.0.0.1:{origin}")).text == "ok"
                assert requests == []
            finally:
                await client.http.aclose()


async def test_http_proxy_routes_plain_http(monkeypatch: pytest.MonkeyPatch):
    requests: list[bytes] = []

    async def forward(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        requests.append(await reader.readuntil(b"\r\n\r\n"))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()

    async with listen(forward) as proxy:
        monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{proxy}")
        client = Client()
        try:
            assert (await client.get("http://example.test/resource")).text == "ok"
            assert len(requests) == 1
            assert requests[0].startswith(b"GET http://example.test/resource HTTP/1.1\r\n")
        finally:
            await client.http.aclose()


@pytest.mark.parametrize("failure", [None, "proxy_ca", "origin_ca", "default_proxy_ca"])
async def test_https_proxy_has_separate_tls_context(authorities: tuple[Authority, Authority], failure: str | None):
    ca, proxy_ca = authorities
    origin_context = ssl.create_default_context(cafile=proxy_ca.path if failure == "origin_ca" else ca.path)
    proxy_context = ssl.create_default_context(cafile=ca.path if failure == "proxy_ca" else proxy_ca.path)
    async with listen(respond, ca.server_context()) as origin:
        async with tunnel(origin, proxy_ca.server_context()) as (proxy_port, requests):
            proxy = httpx2.Proxy(
                f"https://127.0.0.1:{proxy_port}",
                ssl_context=None if failure == "default_proxy_ca" else proxy_context,
            )
            async with httpx2.AsyncClient(verify=origin_context, proxy=proxy, trust_env=False) as raw:
                client = Client(_http=raw)
                if failure:
                    with pytest.raises(httpx2.ConnectError, match="(?i)certificate"):
                        await client.get(f"https://127.0.0.1:{origin}")
                else:
                    assert (await client.get(f"https://127.0.0.1:{origin}")).text == "ok"
                assert len(requests) == (0 if failure in ("proxy_ca", "default_proxy_ca") else 1)
                assert not raw.is_closed


async def test_failing_proxy_is_not_bypassed(authorities: tuple[Authority, Authority], monkeypatch: pytest.MonkeyPatch):
    ca, _ = authorities
    monkeypatch.setenv("SSL_CERT_FILE", str(ca.path))
    origin_requests: list[bytes] = []

    async def origin_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        origin_requests.append(await reader.readuntil(b"\r\n\r\n"))

    async def reject(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()

    async with listen(origin_handler, ca.server_context()) as origin:
        async with listen(reject) as proxy:
            monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy}")
            client = Client()
            try:
                with pytest.raises(httpx2.ProxyError, match="407"):
                    await client.get(f"https://127.0.0.1:{origin}")
                assert origin_requests == []
            finally:
                await client.http.aclose()
