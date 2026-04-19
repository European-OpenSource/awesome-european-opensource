"""Shared fixtures for issue_to_pr tests."""

import pytest


VALID_ISSUE_BODY = """\
### Project Name

CertMate

### Description

SSL certificate management tool for automated certificate monitoring.

### Category

app

### Country

Italy

### Platform

GitHub

### Repository URL

https://github.com/fabriziosalmi/certmate

### License

MIT

### Language

Python

### Owner Name

Fabrizio Salmi

### Owner Type

individual

### Owner Description

_No response_

### Owner Website URL

_No response_

### Is a Startup

No

### Documentation URL

https://docs.certmate.example.com

### Tags

ssl, certificate, monitoring

### Terms & Conditions

- [x] I have read and accept the Terms & Conditions
"""


@pytest.fixture
def valid_issue_body() -> str:
    return VALID_ISSUE_BODY


@pytest.fixture
def minimal_issue_body() -> str:
    """Issue body with only required fields filled in."""
    return """\
### Project Name

MyProject

### Description

A useful open-source project.

### Category

cli

### Country

France

### Platform

GitLab

### Repository URL

https://gitlab.com/owner/myproject

### License

Apache-2.0

### Language

Go

### Owner Name

_No response_

### Owner Type

_No response_

### Owner Description

_No response_

### Owner Website URL

_No response_

### Is a Startup

_No response_

### Documentation URL

_No response_

### Tags

_No response_

### Terms & Conditions

- [x] I have read and accept the Terms & Conditions
"""
