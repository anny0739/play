# Email Validation Service Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an enterprise-grade Python email validation service that validates RFC syntax (including sub-addressing), Internationalized Domain Names (IDN/IDNA), and DNS MX records.

**Architecture:** A layered validation pipeline — syntax → IDN normalization → DNS check — each layer isolated in its own module. The public surface is a single `EmailValidator` facade that orchestrates the layers and returns structured `ValidationResult` objects. DNS queries are async to avoid blocking under load.

**Tech Stack:** Python 3.11+, `dnspython` (DNS queries), `idna` (IDNA 2008), `pytest` + `pytest-asyncio` (tests), `asyncio` (async DNS)

---

## File Map

```
email-validator/
├── pyproject.toml               # Project metadata, dependencies
├── email_validator/
│   ├── __init__.py              # Public API re-exports
│   ├── exceptions.py            # Domain-specific exception hierarchy
│   ├── result.py                # ValidationResult dataclass
│   ├── syntax.py                # RFC 5321/5322 local + domain syntax validation
│   ├── idn.py                   # IDN/IDNA 2008 normalization
│   ├── dns_checker.py           # Async DNS MX/A record verification
│   └── validator.py             # EmailValidator facade (orchestrates layers)
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── test_syntax.py           # Syntax validation unit tests
    ├── test_idn.py              # IDN normalization unit tests
    ├── test_dns_checker.py      # DNS checker unit tests (mocked DNS)
    └── test_validator.py        # Integration tests for EmailValidator
```

---

## Chunk 1: Foundation

### Task 1: Project Setup

**Files:**
- Create: `email-validator/pyproject.toml`
- Create: `email-validator/email_validator/__init__.py`

- [ ] **Step 1: Create project directory and pyproject.toml**

```toml
# email-validator/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "email-validator"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "dnspython>=2.6",
    "idna>=3.7",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.12",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install dependencies**

```bash
cd email-validator
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed email-validator-1.0.0 ...`

- [ ] **Step 3: Create empty package init**

```python
# email-validator/email_validator/__init__.py
from .validator import EmailValidator
from .result import ValidationResult

__all__ = ["EmailValidator", "ValidationResult"]
```

- [ ] **Step 4: Create tests directory with conftest**

```python
# email-validator/tests/conftest.py
import pytest

VALID_EMAILS = [
    "user@example.com",
    "user+tag@example.com",          # sub-addressing
    "user.name+tag@sub.example.co",
    "用户@例子.广告",                   # full internationalized
    "user@münchen.de",               # IDN domain
    '"quoted local"@example.com',    # quoted local part
    "user@[192.168.1.1]",            # IP domain literal
]

INVALID_EMAILS = [
    "",
    "plainaddress",
    "@nodomain.com",
    "noatsign",
    "user@",
    "user@ example.com",            # space in domain
    "user@example..com",            # consecutive dots
    "a" * 65 + "@example.com",      # local part too long (>64)
    "user@" + "a" * 256 + ".com",   # domain too long (>255)
    "user@@example.com",
]
```

- [ ] **Step 5: Commit**

```bash
git add email-validator/
git commit -m "feat: scaffold email-validator project structure"
```

---

### Task 2: ValidationResult and Exceptions

**Files:**
- Create: `email-validator/email_validator/result.py`
- Create: `email-validator/email_validator/exceptions.py`
- Test: `email-validator/tests/test_result.py` (inline in this task)

- [ ] **Step 1: Write failing test for ValidationResult**

```python
# email-validator/tests/test_result.py
from email_validator.result import ValidationResult

def test_valid_result_has_normalized_email():
    r = ValidationResult(
        email="user@example.com",
        normalized_email="user@example.com",
        local_part="user",
        domain="example.com",
        is_valid=True,
    )
    assert r.is_valid is True
    assert r.normalized_email == "user@example.com"
    assert r.error is None

def test_invalid_result_carries_error():
    r = ValidationResult(
        email="bad",
        normalized_email=None,
        local_part=None,
        domain=None,
        is_valid=False,
        error="Invalid format",
    )
    assert r.is_valid is False
    assert r.error == "Invalid format"
    assert r.normalized_email is None
```

- [ ] **Step 2: Run test — verify FAIL**

```bash
pytest tests/test_result.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'email_validator.result'`

- [ ] **Step 3: Implement ValidationResult**

```python
# email-validator/email_validator/result.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationResult:
    email: str
    normalized_email: str | None
    local_part: str | None
    domain: str | None
    is_valid: bool
    error: str | None = None
    has_mx_records: bool | None = None
    is_disposable: bool | None = None
```

- [ ] **Step 4: Implement exceptions**

```python
# email-validator/email_validator/exceptions.py

class EmailValidationError(ValueError):
    """Base class for all email validation failures."""

class SyntaxError(EmailValidationError):
    """RFC syntax violation."""

class IDNError(EmailValidationError):
    """Internationalized domain name encoding failure."""

class DNSError(EmailValidationError):
    """DNS resolution failure (network or configuration)."""

class MXNotFoundError(DNSError):
    """Domain has no MX or A records — cannot receive mail."""
```

- [ ] **Step 5: Run tests — verify PASS**

```bash
pytest tests/test_result.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add email_validator/result.py email_validator/exceptions.py tests/test_result.py
git commit -m "feat: add ValidationResult dataclass and exception hierarchy"
```

---

## Chunk 2: Syntax Validation

### Task 3: Local Part Syntax (RFC 5321/5322)

**Files:**
- Create: `email-validator/email_validator/syntax.py`
- Test: `email-validator/tests/test_syntax.py`

Local part rules:
- Max 64 characters
- Unquoted: `[a-zA-Z0-9!#$%&'*+/=?^_`{|}~.-]` — no leading/trailing/consecutive dots
- Quoted: any printable ASCII inside double-quotes
- Sub-addressing: `local+tag` — the `+tag` portion is preserved, `local` is the canonical mailbox

- [ ] **Step 1: Write failing tests for local part parsing**

```python
# email-validator/tests/test_syntax.py
import pytest
from email_validator.syntax import parse_local_part, parse_domain, split_email
from email_validator.exceptions import SyntaxError as EmailSyntaxError

# --- split_email ---

def test_split_email_basic():
    local, domain = split_email("user@example.com")
    assert local == "user"
    assert domain == "example.com"

def test_split_email_no_at_raises():
    with pytest.raises(EmailSyntaxError, match="missing '@'"):
        split_email("noatsign")

def test_split_email_multiple_at_raises():
    with pytest.raises(EmailSyntaxError, match="multiple '@'"):
        split_email("user@@example.com")

def test_split_email_empty_raises():
    with pytest.raises(EmailSyntaxError, match="empty"):
        split_email("")

# --- parse_local_part ---

def test_parse_local_simple():
    result = parse_local_part("user")
    assert result.canonical == "user"
    assert result.tag is None

def test_parse_local_with_subaddress():
    result = parse_local_part("user+newsletter")
    assert result.canonical == "user"
    assert result.tag == "newsletter"

def test_parse_local_dots_allowed():
    result = parse_local_part("first.last")
    assert result.canonical == "first.last"

def test_parse_local_quoted():
    result = parse_local_part('"quoted local"')
    assert result.canonical == '"quoted local"'

def test_parse_local_too_long_raises():
    with pytest.raises(EmailSyntaxError, match="local part exceeds 64"):
        parse_local_part("a" * 65)

def test_parse_local_leading_dot_raises():
    with pytest.raises(EmailSyntaxError, match="dot"):
        parse_local_part(".user")

def test_parse_local_trailing_dot_raises():
    with pytest.raises(EmailSyntaxError, match="dot"):
        parse_local_part("user.")

def test_parse_local_consecutive_dots_raise():
    with pytest.raises(EmailSyntaxError, match="consecutive dots"):
        parse_local_part("user..name")

def test_parse_local_invalid_char_raises():
    with pytest.raises(EmailSyntaxError, match="invalid character"):
        parse_local_part("user name")  # space not allowed unquoted

# --- parse_domain ---

def test_parse_domain_simple():
    assert parse_domain("example.com") == "example.com"

def test_parse_domain_subdomain():
    assert parse_domain("mail.sub.example.com") == "mail.sub.example.com"

def test_parse_domain_too_long_raises():
    with pytest.raises(EmailSyntaxError, match="domain exceeds 255"):
        parse_domain("a" * 256 + ".com")

def test_parse_domain_consecutive_dots_raise():
    with pytest.raises(EmailSyntaxError, match="consecutive dots"):
        parse_domain("example..com")

def test_parse_domain_leading_hyphen_label_raises():
    with pytest.raises(EmailSyntaxError, match="hyphen"):
        parse_domain("-bad.example.com")

def test_parse_domain_ip_literal():
    assert parse_domain("[192.168.1.1]") == "[192.168.1.1]"
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/test_syntax.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'email_validator.syntax'`

- [ ] **Step 3: Implement syntax.py**

```python
# email-validator/email_validator/syntax.py
import re
from dataclasses import dataclass
from .exceptions import SyntaxError as EmailSyntaxError

# RFC 5321/5322 unquoted local part allowed characters
_UNQUOTED_LOCAL_RE = re.compile(r'^[a-zA-Z0-9!#$%&\'*+/=?^_`{|}~.\-]+$')
_IP_LITERAL_RE = re.compile(
    r'^\[(\d{1,3}\.){3}\d{1,3}\]$'
)
_LABEL_RE = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?$')


@dataclass(frozen=True)
class LocalPartInfo:
    canonical: str       # full local part as provided
    tag: str | None      # sub-address tag (after '+'), or None


def split_email(email: str) -> tuple[str, str]:
    """Split email into (local, domain). Raises SyntaxError on malformed input."""
    if not email:
        raise EmailSyntaxError("empty email address")
    parts = email.split("@")
    if len(parts) < 2:
        raise EmailSyntaxError("missing '@' in email address")
    if len(parts) > 2:
        raise EmailSyntaxError("multiple '@' characters in email address")
    local, domain = parts
    if not local:
        raise EmailSyntaxError("empty local part")
    if not domain:
        raise EmailSyntaxError("empty domain part")
    return local, domain


def parse_local_part(local: str) -> LocalPartInfo:
    """
    Validate and parse an email local part.
    Supports unquoted atoms, quoted strings, and sub-addressing (user+tag).
    """
    if len(local) > 64:
        raise EmailSyntaxError(f"local part exceeds 64 characters ({len(local)})")

    # Quoted local part — minimal validation: must be printable ASCII
    if local.startswith('"') and local.endswith('"'):
        inner = local[1:-1]
        if not all(32 <= ord(c) <= 126 for c in inner):
            raise EmailSyntaxError("quoted local part contains non-printable characters")
        return LocalPartInfo(canonical=local, tag=None)

    # Sub-address split on first '+'
    tag: str | None = None
    base = local
    if "+" in local:
        idx = local.index("+")
        base = local[:idx]
        tag = local[idx + 1:]
        if not base:
            raise EmailSyntaxError("local part cannot start with '+'")

    # Validate base (and full local if no sub-address)
    _validate_unquoted_atom(base)
    return LocalPartInfo(canonical=local, tag=tag)


def _validate_unquoted_atom(atom: str) -> None:
    if atom.startswith("."):
        raise EmailSyntaxError("local part dot: cannot start with a dot")
    if atom.endswith("."):
        raise EmailSyntaxError("local part dot: cannot end with a dot")
    if ".." in atom:
        raise EmailSyntaxError("local part consecutive dots are not allowed")
    if not _UNQUOTED_LOCAL_RE.match(atom):
        raise EmailSyntaxError(f"invalid character in local part: '{atom}'")


def parse_domain(domain: str) -> str:
    """
    Validate a domain string (ASCII). Returns domain unchanged if valid.
    Accepts IP literals like [192.168.1.1].
    IDN (Unicode) domains must be encoded before calling this function.
    """
    if _IP_LITERAL_RE.match(domain):
        return domain

    if len(domain) > 255:
        raise EmailSyntaxError(f"domain exceeds 255 characters ({len(domain)})")

    if ".." in domain:
        raise EmailSyntaxError("domain has consecutive dots")

    labels = domain.split(".")
    for label in labels:
        if not label:
            raise EmailSyntaxError("domain has empty label (leading/trailing dot)")
        if label.startswith("-") or label.endswith("-"):
            raise EmailSyntaxError(f"domain label '{label}' starts or ends with hyphen")
        if not _LABEL_RE.match(label):
            raise EmailSyntaxError(f"domain label '{label}' contains invalid characters")

    return domain
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/test_syntax.py -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add email_validator/syntax.py tests/test_syntax.py
git commit -m "feat: RFC 5321/5322 local part and domain syntax validation"
```

---

## Chunk 3: IDN Support

### Task 4: IDN/IDNA 2008 Normalization

**Files:**
- Create: `email-validator/email_validator/idn.py`
- Test: `email-validator/tests/test_idn.py`

IDNA 2008 converts Unicode domain labels to ACE punycode (`xn--...`).
The `idna` library implements IDNA 2008 (unlike Python's built-in `encodings.idna` which is IDNA 2003).

- [ ] **Step 1: Write failing tests**

```python
# email-validator/tests/test_idn.py
import pytest
from email_validator.idn import encode_domain, is_idn_domain
from email_validator.exceptions import IDNError

def test_ascii_domain_unchanged():
    assert encode_domain("example.com") == "example.com"

def test_unicode_domain_encodes_to_ace():
    # münchen.de -> xn--mnchen-3ya.de
    result = encode_domain("münchen.de")
    assert result == "xn--mnchen-3ya.de"

def test_fully_unicode_domain():
    # 例子.广告 (Chinese) -> xn--fsqu00a.xn--fiqs8sirgfmh
    result = encode_domain("例子.广告")
    assert result.startswith("xn--")

def test_mixed_ascii_unicode_domain():
    result = encode_domain("mail.münchen.de")
    assert "xn--" in result
    assert result.startswith("mail.")

def test_invalid_idn_raises():
    with pytest.raises(IDNError, match="IDN encoding failed"):
        encode_domain("xn--nxasmq6b.com.")  # trailing dot edge case is ok, but...
        # use a genuinely invalid label:

def test_invalid_label_raises():
    with pytest.raises(IDNError):
        encode_domain("bad_label.com")  # underscore not allowed in IDNA 2008

def test_is_idn_domain_true_for_unicode():
    assert is_idn_domain("münchen.de") is True

def test_is_idn_domain_false_for_ascii():
    assert is_idn_domain("example.com") is False
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/test_idn.py -v
```

Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement idn.py**

```python
# email-validator/email_validator/idn.py
import idna
from .exceptions import IDNError


def is_idn_domain(domain: str) -> bool:
    """Return True if domain contains non-ASCII characters (is internationalized)."""
    try:
        domain.encode("ascii")
        return False
    except UnicodeEncodeError:
        return True


def encode_domain(domain: str) -> str:
    """
    Encode a domain to its ACE (ASCII Compatible Encoding) form using IDNA 2008.
    ASCII-only domains are returned unchanged.
    Raises IDNError if the domain is not valid under IDNA 2008.
    """
    if not is_idn_domain(domain):
        # Still validate ASCII labels via idna for strict IDNA 2008 rules
        try:
            return idna.encode(domain, alabel_round_trip=False).decode("ascii")
        except (idna.core.InvalidCodepoint, idna.core.InvalidCodepointContext,
                UnicodeError, UnicodeDecodeError) as exc:
            raise IDNError(f"IDN encoding failed for '{domain}': {exc}") from exc

    try:
        encoded = idna.encode(domain, alabel_round_trip=False).decode("ascii")
        return encoded
    except (idna.core.InvalidCodepoint, idna.core.InvalidCodepointContext,
            UnicodeError, UnicodeDecodeError) as exc:
        raise IDNError(f"IDN encoding failed for '{domain}': {exc}") from exc
```

- [ ] **Step 4: Fix the invalid_idn test — it must use a genuinely invalid IDN label**

Update `tests/test_idn.py` — replace the confusing placeholder test:

```python
def test_invalid_label_raises():
    with pytest.raises(IDNError):
        encode_domain("bad\x00label.com")  # null byte — invalid in any label
```

- [ ] **Step 5: Run tests — verify PASS**

```bash
pytest tests/test_idn.py -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add email_validator/idn.py tests/test_idn.py
git commit -m "feat: IDNA 2008 domain encoding via idna library"
```

---

## Chunk 4: DNS MX Checker

### Task 5: Async DNS MX Record Verification

**Files:**
- Create: `email-validator/email_validator/dns_checker.py`
- Test: `email-validator/tests/test_dns_checker.py`

Rules:
- Query DNS for MX records on the domain
- Fall back to A records if no MX found (some domains accept mail via A record)
- Raise `MXNotFoundError` if neither MX nor A records exist
- Respect a configurable timeout (default 10s)
- Async so multiple validations can run concurrently

- [ ] **Step 1: Write failing tests (with mocked DNS)**

```python
# email-validator/tests/test_dns_checker.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import dns.resolver
from email_validator.dns_checker import check_mx, MXCheckResult
from email_validator.exceptions import MXNotFoundError, DNSError


@pytest.fixture
def mock_mx_answer():
    """Fake dns answer with one MX record."""
    answer = MagicMock()
    answer.__iter__ = MagicMock(return_value=iter([MagicMock()]))
    return answer


@pytest.mark.asyncio
async def test_valid_mx_returns_true(mock_mx_answer):
    with patch("email_validator.dns_checker.dns.asyncresolver.resolve",
               AsyncMock(return_value=mock_mx_answer)):
        result = await check_mx("example.com")
    assert result.has_mx is True
    assert result.domain == "example.com"


@pytest.mark.asyncio
async def test_no_mx_falls_back_to_a_record(mock_mx_answer):
    async def side_effect(domain, record_type, **kwargs):
        if record_type == "MX":
            raise dns.resolver.NoAnswer
        return mock_mx_answer  # A record found

    with patch("email_validator.dns_checker.dns.asyncresolver.resolve",
               AsyncMock(side_effect=side_effect)):
        result = await check_mx("example.com")
    assert result.has_mx is True  # A record fallback counts


@pytest.mark.asyncio
async def test_nxdomain_raises_mx_not_found():
    with patch("email_validator.dns_checker.dns.asyncresolver.resolve",
               AsyncMock(side_effect=dns.resolver.NXDOMAIN)):
        with pytest.raises(MXNotFoundError, match="no MX or A records"):
            await check_mx("nonexistent-domain-xyz.com")


@pytest.mark.asyncio
async def test_both_mx_and_a_missing_raises():
    with patch("email_validator.dns_checker.dns.asyncresolver.resolve",
               AsyncMock(side_effect=dns.resolver.NoAnswer)):
        with pytest.raises(MXNotFoundError):
            await check_mx("no-records.example.com")


@pytest.mark.asyncio
async def test_timeout_raises_dns_error():
    with patch("email_validator.dns_checker.dns.asyncresolver.resolve",
               AsyncMock(side_effect=dns.resolver.Timeout)):
        with pytest.raises(DNSError, match="timed out"):
            await check_mx("slow.example.com")
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/test_dns_checker.py -v
```

Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement dns_checker.py**

```python
# email-validator/email_validator/dns_checker.py
import asyncio
from dataclasses import dataclass
import dns.asyncresolver
import dns.resolver
from .exceptions import DNSError, MXNotFoundError


@dataclass(frozen=True)
class MXCheckResult:
    domain: str
    has_mx: bool
    records: list[str]   # MX hostnames or A IPs


async def check_mx(domain: str, timeout: float = 10.0) -> MXCheckResult:
    """
    Check whether `domain` can receive email by looking up MX records.
    Falls back to A records if no MX records are found.
    Raises MXNotFoundError if neither exists.
    Raises DNSError on timeout or resolver misconfiguration.
    """
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = timeout
    resolver.lifetime = timeout

    # Try MX first
    try:
        answer = await dns.asyncresolver.resolve(domain, "MX", lifetime=timeout)
        records = [str(r.exchange).rstrip(".") for r in answer]
        return MXCheckResult(domain=domain, has_mx=True, records=records)
    except dns.resolver.NXDOMAIN:
        raise MXNotFoundError(f"'{domain}' has no MX or A records (NXDOMAIN)")
    except dns.resolver.Timeout:
        raise DNSError(f"DNS query for '{domain}' timed out")
    except dns.resolver.NoAnswer:
        pass  # fall through to A record lookup

    # Fallback: A record
    try:
        answer = await dns.asyncresolver.resolve(domain, "A", lifetime=timeout)
        records = [str(r) for r in answer]
        return MXCheckResult(domain=domain, has_mx=True, records=records)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        raise MXNotFoundError(f"'{domain}' has no MX or A records — cannot receive mail")
    except dns.resolver.Timeout:
        raise DNSError(f"DNS A-record query for '{domain}' timed out")
```

- [ ] **Step 4: Run tests — verify PASS**

```bash
pytest tests/test_dns_checker.py -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add email_validator/dns_checker.py tests/test_dns_checker.py
git commit -m "feat: async DNS MX/A record checker with fallback"
```

---

## Chunk 5: Main Validator Facade

### Task 6: EmailValidator Orchestration

**Files:**
- Create: `email-validator/email_validator/validator.py`
- Test: `email-validator/tests/test_validator.py`

The validator runs:
1. Split email (syntax)
2. Parse local part (syntax + sub-addressing)
3. Encode domain (IDN)
4. Validate domain ASCII syntax
5. Check MX (optional — can be disabled for offline use)

- [ ] **Step 1: Write failing tests**

```python
# email-validator/tests/test_validator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from email_validator.validator import EmailValidator
from email_validator.dns_checker import MXCheckResult


@pytest.fixture
def validator():
    return EmailValidator(check_dns=False)


@pytest.fixture
def validator_with_dns():
    return EmailValidator(check_dns=True)


# --- Offline validation (no DNS) ---

def test_valid_simple_email(validator):
    result = validator.validate("user@example.com")
    assert result.is_valid is True
    assert result.local_part == "user"
    assert result.domain == "example.com"
    assert result.error is None

def test_subaddress_parsed(validator):
    result = validator.validate("user+newsletter@example.com")
    assert result.is_valid is True
    assert result.local_part == "user+newsletter"

def test_invalid_email_no_at(validator):
    result = validator.validate("noatsign")
    assert result.is_valid is False
    assert result.error is not None

def test_local_part_too_long(validator):
    result = validator.validate("a" * 65 + "@example.com")
    assert result.is_valid is False

def test_total_length_too_long(validator):
    result = validator.validate("user@" + "a" * 256 + ".com")
    assert result.is_valid is False

def test_idn_domain_normalized(validator):
    result = validator.validate("user@münchen.de")
    assert result.is_valid is True
    assert result.domain == "xn--mnchen-3ya.de"

def test_normalized_email_uses_encoded_domain(validator):
    result = validator.validate("user@münchen.de")
    assert result.normalized_email == "user@xn--mnchen-3ya.de"


# --- Online validation (with DNS) ---

@pytest.mark.asyncio
async def test_valid_email_with_dns(validator_with_dns):
    mx_result = MXCheckResult(domain="example.com", has_mx=True, records=["mail.example.com"])
    with patch("email_validator.validator.check_mx", AsyncMock(return_value=mx_result)):
        result = await validator_with_dns.validate_async("user@example.com")
    assert result.is_valid is True
    assert result.has_mx_records is True

@pytest.mark.asyncio
async def test_invalid_domain_dns_raises(validator_with_dns):
    from email_validator.exceptions import MXNotFoundError
    with patch("email_validator.validator.check_mx",
               AsyncMock(side_effect=MXNotFoundError("no records"))):
        result = await validator_with_dns.validate_async("user@nonexistent.xyz")
    assert result.is_valid is False
    assert "no records" in result.error
```

- [ ] **Step 2: Run tests — verify FAIL**

```bash
pytest tests/test_validator.py -v
```

Expected: `FAILED` — `ModuleNotFoundError`

- [ ] **Step 3: Implement validator.py**

```python
# email-validator/email_validator/validator.py
import asyncio
from .result import ValidationResult
from .syntax import split_email, parse_local_part, parse_domain
from .idn import encode_domain, is_idn_domain
from .dns_checker import check_mx
from .exceptions import EmailValidationError, IDNError, DNSError, MXNotFoundError

_MAX_EMAIL_LENGTH = 320


class EmailValidator:
    """
    Orchestrates RFC syntax, IDN encoding, and optional DNS MX validation.

    Usage:
        validator = EmailValidator(check_dns=False)
        result = validator.validate("user@example.com")

        # With DNS:
        validator = EmailValidator(check_dns=True)
        result = await validator.validate_async("user@example.com")
    """

    def __init__(self, check_dns: bool = False, dns_timeout: float = 10.0):
        self.check_dns = check_dns
        self.dns_timeout = dns_timeout

    def validate(self, email: str) -> ValidationResult:
        """
        Synchronous validation (syntax + IDN only; no DNS).
        Ignores `check_dns` setting — use validate_async for DNS.
        """
        return self._validate_syntax(email)

    async def validate_async(self, email: str) -> ValidationResult:
        """
        Full validation including optional DNS MX check.
        """
        result = self._validate_syntax(email)
        if not result.is_valid or not self.check_dns:
            return result

        try:
            mx_result = await check_mx(result.domain, timeout=self.dns_timeout)
            return ValidationResult(
                email=result.email,
                normalized_email=result.normalized_email,
                local_part=result.local_part,
                domain=result.domain,
                is_valid=True,
                has_mx_records=mx_result.has_mx,
            )
        except MXNotFoundError as exc:
            return ValidationResult(
                email=email,
                normalized_email=None,
                local_part=result.local_part,
                domain=result.domain,
                is_valid=False,
                error=str(exc),
                has_mx_records=False,
            )
        except DNSError as exc:
            return ValidationResult(
                email=email,
                normalized_email=None,
                local_part=result.local_part,
                domain=result.domain,
                is_valid=False,
                error=f"DNS error: {exc}",
            )

    def _validate_syntax(self, email: str) -> ValidationResult:
        if len(email) > _MAX_EMAIL_LENGTH:
            return self._failure(email, f"email exceeds {_MAX_EMAIL_LENGTH} characters")

        try:
            local, raw_domain = split_email(email)
        except EmailValidationError as exc:
            return self._failure(email, str(exc))

        try:
            parse_local_part(local)
        except EmailValidationError as exc:
            return self._failure(email, str(exc))

        # IDN encode domain
        try:
            domain = encode_domain(raw_domain)
        except IDNError as exc:
            return self._failure(email, str(exc))

        # ASCII syntax check on encoded domain
        try:
            parse_domain(domain)
        except EmailValidationError as exc:
            return self._failure(email, str(exc))

        normalized = f"{local}@{domain}"
        return ValidationResult(
            email=email,
            normalized_email=normalized,
            local_part=local,
            domain=domain,
            is_valid=True,
        )

    @staticmethod
    def _failure(email: str, error: str) -> ValidationResult:
        return ValidationResult(
            email=email,
            normalized_email=None,
            local_part=None,
            domain=None,
            is_valid=False,
            error=error,
        )
```

- [ ] **Step 4: Run all tests**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 5: Commit**

```bash
git add email_validator/validator.py tests/test_validator.py
git commit -m "feat: EmailValidator facade with sync/async validation pipeline"
```

---

## Chunk 6: Integration & Hardening

### Task 7: End-to-End Integration Tests + Edge Cases

**Files:**
- Modify: `email-validator/tests/conftest.py` — add parametrize fixtures
- Create: `email-validator/tests/test_integration.py`

- [ ] **Step 1: Write integration tests against the full fixture list**

```python
# email-validator/tests/test_integration.py
import pytest
from email_validator.validator import EmailValidator

validator = EmailValidator(check_dns=False)


@pytest.mark.parametrize("email", [
    "user@example.com",
    "user+tag@example.com",
    "user.name+tag@sub.example.co",
    '"quoted local"@example.com',
    "user@münchen.de",
    "user@xn--mnchen-3ya.de",
])
def test_valid_emails_pass(email):
    result = validator.validate(email)
    assert result.is_valid, f"Expected {email!r} to be valid, got error: {result.error}"


@pytest.mark.parametrize("email", [
    "",
    "plainaddress",
    "@nodomain.com",
    "noatsign",
    "user@",
    "user@@example.com",
    "user@example..com",
    "a" * 65 + "@example.com",
    "user@" + "a" * 256 + ".com",
    ".user@example.com",
    "user.@example.com",
    "user..name@example.com",
])
def test_invalid_emails_fail(email):
    result = validator.validate(email)
    assert not result.is_valid, f"Expected {email!r} to be invalid but it passed"
    assert result.error is not None
```

- [ ] **Step 2: Run full suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration tests for valid/invalid email corpus"
```

---

### Task 8: Package Public API Cleanup

**Files:**
- Modify: `email-validator/email_validator/__init__.py`

- [ ] **Step 1: Expose clean public API**

```python
# email-validator/email_validator/__init__.py
from .validator import EmailValidator
from .result import ValidationResult
from .exceptions import (
    EmailValidationError,
    SyntaxError as EmailSyntaxError,
    IDNError,
    DNSError,
    MXNotFoundError,
)

__all__ = [
    "EmailValidator",
    "ValidationResult",
    "EmailValidationError",
    "EmailSyntaxError",
    "IDNError",
    "DNSError",
    "MXNotFoundError",
]
```

- [ ] **Step 2: Run full suite one final time**

```bash
pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 3: Final commit**

```bash
git add email_validator/__init__.py
git commit -m "feat: clean public API for email-validator package"
```

---

## Usage Reference

```python
from email_validator import EmailValidator

# Offline (syntax + IDN only)
v = EmailValidator()
result = v.validate("user+newsletter@münchen.de")
print(result.is_valid)          # True
print(result.normalized_email)  # user+newsletter@xn--mnchen-3ya.de
print(result.local_part)        # user+newsletter

# Online (adds async DNS MX check)
import asyncio
v = EmailValidator(check_dns=True, dns_timeout=5.0)
result = asyncio.run(v.validate_async("user@gmail.com"))
print(result.has_mx_records)    # True
```
