# Multi-Tenant Security Lab

### Exploring Improved Tenant Resolution, Context Isolation, and Concurrent Request Handling

An independent Python backend prototype exploring tenant identification, JWT authentication, context lifecycle management, and concurrent request handling in multi-tenant SaaS applications.

**Status:** Prototype — real MongoDB tenant routing and database isolation are future improvements.

---

## Table of Contents

1. [Overview](#overview)
2. [Problem Statement](#problem-statement)
3. [Architectural Approach](#architectural-approach)
4. [Improvements Explored](#improvements-explored)
5. [Technology Stack](#technology-stack)
6. [System Architecture](#system-architecture)
7. [Authentication and Tenant Resolution](#authentication-and-tenant-resolution)
8. [ContextVar and Context Lifecycle](#contextvar-and-context-lifecycle)
9. [Load Testing and Results](#load-testing-and-results)
10. [Current Implementation](#current-implementation)
11. [Limitations](#limitations)
12. [Future Improvements](#future-improvements)
13. [Running Locally](#running-locally)
14. [Project Structure](#project-structure)
15. [Security Considerations](#security-considerations)
16. [Disclaimer](#disclaimer)

---

## Overview

Multi-tenant SaaS applications serve multiple organizations through a shared application. Each request must be associated with the correct tenant, and the application must prevent users from accessing another organization's data without authorization.

This project explores an alternative approach to tenant resolution and execution-context management.

The prototype uses:

- JWT-based authentication.
- Tenant identification from a validated JWT.
- Python `ContextVar` for context-local tenant state.
- A context manager for explicit tenant-context lifecycle management.
- Mock users associated with distinct tenant identifiers.
- Concurrent HTTP requests to test tenant selection.

The main objective is to investigate how tenant context can be managed more explicitly and safely, especially in applications that may use asynchronous Python execution.

## Problem Statement

A multi-tenant application must reliably identify the organization associated with every authenticated request.

Potential risks include:

- Trusting a tenant database name supplied directly by the client.
- Accidentally retaining tenant context after an operation completes.
- Incorrectly sharing tenant state between concurrent operations.
- Resolving a tenant without verifying that the user is authorized to access it.
- Routing a database operation to the wrong tenant's data.

This prototype focuses on tenant identification and context lifecycle management. It is an architectural learning exercise, not a complete production security solution.

## Architectural Approach

The project explores an alternative to a design in which a client supplies a tenant identifier, middleware stores it in thread-local state, and downstream code reads that state.

The independent prototype investigates three changes:

1. **Tenant resolution:** Extract the tenant identifier from a validated authentication token rather than trusting an arbitrary tenant identifier supplied in a request.
2. **Context storage:** Use `ContextVar` instead of relying on `threading.local()` for context-local state.
3. **Context lifecycle:** Use a context manager to establish the tenant context and restore the previous context when the operation completes.

These changes aim to make tenant identification and context handling more explicit.

They do not automatically guarantee database isolation or eliminate every concurrency or authorization risk.

## Improvements Explored

### 1. Tenant Resolution Through JWT

**Earlier approach being explored:** The client supplies a tenant database name, which the application uses during tenant resolution.

**Prototype approach:** The server issues a JWT containing a tenant identifier after successful login. Subsequent requests validate the token before extracting the tenant identifier.

Benefits:

- Reduces reliance on untrusted client-supplied tenant names.
- Provides a consistent source of tenant identity for authenticated requests.
- Supports a clearer authentication-to-tenant-resolution flow.

A valid JWT is not sufficient on its own. The application must also verify that the user is authorized for the selected tenant and that the token has not expired or been otherwise invalidated according to the application's token policy.

### 2. ContextVar Instead of Thread-Local Storage

Python's `threading.local()` associates state with an operating-system thread. It can be appropriate for threaded applications, but thread-local state does not provide the same context semantics as `ContextVar` for asynchronous tasks.

This prototype uses `ContextVar` to represent the current tenant execution context.

Benefits:

- Context-local state suited to asynchronous Python execution.
- Explicit context access through a shared helper.
- Less dependence on the assumption that a request's state belongs exclusively to a particular thread.

`ContextVar` does not eliminate thread overhead or guarantee isolation automatically. Correct propagation and cleanup of context are still necessary.

### 3. Explicit Context Lifecycle Management

The prototype uses a context manager to establish and restore tenant context.

Benefits:

- Cleanup is handled in a `finally` block.
- The previous context is restored even when an exception occurs.
- Context lifecycle is visible at the operation boundary.
- Nested contexts can restore the value that existed before entering the inner context.

This helps reduce the risk of stale tenant state being used by later operations.

### 4. Concurrent Tenant Selection Testing

The prototype uses 1,000 mock users associated with 1,000 distinct tenant identifiers.

Each user authenticates separately and sends an employee API request with their own JWT. The test compares the returned tenant identifier against the expected tenant for that user.

This tests tenant selection under concurrent HTTP traffic. It does not establish that real database queries are isolated.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend implementation |
| Django | Web application framework |
| Django REST Framework | API endpoints |
| PyJWT | JWT creation and validation |
| `contextvars.ContextVar` | Context-local tenant state |
| `contextlib.contextmanager` | Tenant context lifecycle |
| `aiohttp` | Asynchronous HTTP load testing |
| Git and GitHub | Version control and project documentation |

## System Architecture

```text
                         Client
                            |
                            v
                       Login API
                            |
                            v
                     Mock User Registry
                            |
                            v
                  JWT with Tenant Identifier
                            |
                            v
                   Authenticated API Request
                            |
                            v
                     JWT Validation
                            |
                            v
                 Extract Tenant Identifier
                            |
                            v
                  Tenant Context Manager
                            |
                            v
                     Set ContextVar
                            |
                            v
                    Process API Operation
                            |
                            v
                    Reset Previous Context
                            |
                            v
                      API Response
```

### Current Architecture Boundary

The current implementation stops at tenant selection and context management.

It does not yet connect this flow to actual MongoDB reads or writes. Real database routing and cross-tenant database isolation are future implementation goals.

## Authentication and Tenant Resolution

The prototype follows this simplified flow:

1. The user submits credentials to the login API.
2. The application checks the credentials against a mock user registry.
3. The server issues a JWT containing user information and a tenant identifier.
4. The client sends the JWT in the `Authorization` header.
5. The authentication component validates the token.
6. The application extracts the tenant identifier from the validated token.
7. The tenant context is established for the operation.
8. The context is restored when the operation finishes.

Example request header:

```http
Authorization: Bearer <access_token>
```

The tenant identifier must not be accepted merely because it appears in a request. It must come from a validated token and be checked against the application's authorization rules.

## ContextVar and Context Lifecycle

The tenant context is stored using Python's `ContextVar`.

A simplified implementation looks like this:

```python
from contextvars import ContextVar
from contextlib import contextmanager

tenant_context = ContextVar("tenant_db", default=None)


def get_current_tenant_db():
    return tenant_context.get()


@contextmanager
def tenant_db_context(tenant_db):
    token = tenant_context.set(tenant_db)

    try:
        yield
    finally:
        tenant_context.reset(token)
```

Example usage:

```python
with tenant_db_context("vsuite_company_A"):
    current_tenant = get_current_tenant_db()
    # Process the operation for this tenant
```

If the previous context was `None`, the context changes as follows:

```text
Before operation:  None
During operation:  vsuite_company_A
After operation:   None
```

The token returned by `ContextVar.set()` allows `reset()` to restore the previous value instead of unconditionally setting it to `None`.

This is useful for reliable context cleanup and nested context management.

## Load Testing and Results

The prototype was tested locally using 1,000 distinct mock users, each associated with a different tenant identifier.

Each authenticated user sent one employee API request. The load test verified whether the tenant identifier returned by the API matched that user's expected tenant.

### Recorded Results

| Metric | Result |
|---|---:|
| Unique mock users | 1,000 |
| Unique mock tenant identifiers | 1,000 |
| Successful logins | 1,000 |
| Employee API requests | 1,000 |
| Concurrency limit | 100 |
| Successful requests | 1,000 |
| Failed or incorrect requests | 0 |
| Tenant mismatches | 0 |
| Total request time | 3.65 seconds |
| Measured throughput | 273.89 requests/second |
| Approximate p95 latency | 3,560.39 ms |

These are results from one local test run and may vary with the hardware, server configuration, and workload.

The p95 latency is approximately 3.56 seconds, despite the total measured request phase taking 3.65 seconds. The load-test timing and latency distribution should be reviewed before using these figures for performance comparisons.

### What the Test Demonstrates

- The mock user registry authenticated all 1,000 test users.
- Each user received a token.
- The employee API returned the expected tenant identifier for every tested request.
- The test recorded zero failed or incorrect requests.
- The test recorded zero tenant mismatches at a concurrency limit of 100.

### What the Test Does Not Demonstrate

- Actual MongoDB database isolation.
- Correct routing of MongoDB reads and writes.
- Resistance to every possible cross-tenant authorization attack.
- Production capacity or performance.
- Behavior under every thread, async-task, and database-connection configuration.

## Current Implementation

The current prototype includes:

- A mock user registry with 1,000 additional test users.
- JWT issuance and validation.
- An authenticated employee API endpoint.
- Tenant context management using `ContextVar`.
- Context cleanup through a context manager.
- A load-testing script that authenticates unique users and validates returned tenant identifiers.

The prototype is focused on tenant-context isolation, not on implementing a complete SaaS platform.

## Limitations

The following limitations are acknowledged:

1. **No real MongoDB routing:** The prototype does not currently connect tenant context to actual database operations.
2. **Mock credentials:** The test registry is for local experimentation and is not suitable for production authentication.
3. **Incomplete authorization:** Full tenant membership validation and role-based authorization require further implementation and testing.
4. **Limited load testing:** The recorded benchmark is a single local run.
5. **No production deployment validation:** Deployment, observability, failure recovery, and production security controls are outside the current scope.

## Future Improvements

### Phase 1: Strengthen Authentication

- Replace plaintext mock passwords with secure password hashing.
- Add robust credential validation and consistent error handling.
- Configure secure JWT expiration and token lifecycle policies.
- Validate tenant membership and user permissions.
- Protect signing secrets using environment-based configuration.
- Add automated tests for invalid, expired, and tampered tokens.

### Phase 2: Verify Context Isolation

- Add automated tests for context restoration after exceptions.
- Test nested tenant contexts.
- Test simultaneous requests using different tenant identifiers.
- Verify that each operation observes only its intended context.
- Test the implementation under supported asynchronous execution patterns.
- Confirm that context is reset correctly across all relevant request paths.

### Phase 3: Implement Real MongoDB Tenant Routing

- Configure MongoDB connections.
- Implement and verify tenant-aware MongoEngine or PyMongo access.
- Ensure tenant selection is resolved correctly for each database operation.
- Test actual reads and writes against separate tenant databases.
- Verify that one tenant cannot retrieve or modify another tenant's records.
- Review connection reuse, database selection, caching, and cleanup behavior.

### Phase 4: Strengthen Tenant Authorization

- Add tenant membership validation.
- Implement role-based access control.
- Add tests for horizontal privilege escalation.
- Reject unauthorized tenant selection.
- Add security tests for malformed or manipulated requests.
- Ensure authorization is enforced at the API and data-access layers.

### Phase 5: Improve Performance Testing

- Repeat benchmarks with consistent test conditions.
- Measure login performance separately from authenticated API requests.
- Improve percentile calculations and timing methodology.
- Record CPU, memory, and server resource usage.
- Test different concurrency levels and request patterns.
- Compare results before and after database integration.

### Phase 6: Production Readiness

- Add structured logging and monitoring.
- Add automated tests and continuous integration.
- Configure secure production settings.
- Implement rate limiting and appropriate request timeouts.
- Add database indexes and query-performance testing where applicable.
- Document deployment, backup, recovery, and incident-response procedures.

## Running Locally

1. Clone the repository.
2. Create a Python virtual environment.
3. Install the dependencies listed in `requirements.txt`.
4. Configure Django for local development.
5. Start the development server:

```bash
python manage.py runserver
```

6. In another terminal, run the load test:

```bash
python load_test.py
```

The load test authenticates the mock users and sends one employee API request per successfully authenticated user.

Use only the included mock credentials in your local learning environment. Do not expose real credentials, signing secrets, or database connection strings in a public repository.

## Project Structure

The exact paths should match the repository. A possible structure is:

```text
multi-tenant-security-lab/
├── manage.py
├── requirements.txt
├── README.md
├── .gitignore
├── load_test.py
└── config/
    ├── authentication.py
    ├── tenant_context.py
    ├── tenant_registry.py
    ├── views.py
    └── urls.py
```
### Alternative: Reusable Tenant Context Decorator

In the current prototype, I use a context manager (`with tenant_db_context(...)`) directly inside the API view. I chose this approach to understand how tenant context is established, maintained, and reset after an operation.

As an alternative, a reusable decorator such as `@tenant_context_required` could manage this lifecycle automatically.

**Current approach:**

```python
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
def employee(request):
    with tenant_db_context(request.auth["tenant_db"]):
        return Response({
            "tenant_db": get_current_tenant_db()
        })
```

**Possible alternative:**

```python
@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@tenant_context_required
def employee(request):
    return Response({
        "tenant_db": get_current_tenant_db()
    })
```

The decorator would establish the tenant context before executing the view and restore the previous context afterward.

**Benefits of the alternative:**
- Reduces repeated context-management code across views.
- Centralizes tenant-context setup and cleanup.
- Keeps view functions focused on business logic.

The decorator is an alternative design, not a claim that the current context-manager implementation is incorrect. It must be implemented and tested before being considered part of the prototype.

## Learning Outcomes

This project explores:

- JWT authentication and tenant identification.
- Context-local state in Python.
- Context managers and cleanup in `finally` blocks.
- Concurrency testing with asynchronous HTTP clients.
- Tenant-selection validation.
- The difference between testing tenant identifiers and proving database isolation.
- Security and authorization requirements for multi-tenant SaaS applications.

## Disclaimer

This is an independent educational prototype created to explore multi-tenant backend design and request-context management.

It is not a production-ready SaaS security implementation and does not claim to replace or reproduce any employer's proprietary architecture or source code.
