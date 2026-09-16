from fastapi import FastAPI
from app.db import Base, engine

app = FastAPI(title='UNG-CERBERUS', version='0.1.0')

@app.on_event('startup')
def startup():
    Base.metadata.create_all(bind=engine)

@app.get('/health')
def health():
    return {'status': 'ok', 'system': 'UNG-CERBERUS'}
