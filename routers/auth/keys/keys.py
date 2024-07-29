with open('routers/auth/keys/private.pem') as f:
    PRIVATE_KEY = f.read()

with open('routers/auth/keys/public.pem') as f:
    PUBLIC_KEY = f.read()