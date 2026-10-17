from contextvars import ContextVar
from contextlib import contextmanager

tenant_context = ContextVar("tenant_db", default=None)

def set_current_tenant_db(tenant_db):
    return tenant_context.set(tenant_db)

def get_current_tenant_db():
    return tenant_context.get()

def reset_current_tenant_db(context_token):
    return tenant_context.reset(context_token)

@contextmanager
def tenant_db_context(tenant_db):
    context_token= set_current_tenant_db(tenant_db)
    try:
        yield
    finally:
        reset_current_tenant_db(context_token)
