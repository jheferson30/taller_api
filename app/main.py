from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.configuracion.base_datos import Base, engine
from app.rutas import economia_ruta, mobile_ruta, movimiento_caja_ruta, ticket_ruta, upload_ruta, vehiculo_ruta, seguridad_ruta, citas_ruta

Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Taller Mecanico")

# Crear directorio de uploads si no existe
os.makedirs("uploads", exist_ok=True)

# Montar directorio de uploads como archivos estáticos
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehiculo_ruta.router)
app.include_router(economia_ruta.router)
app.include_router(movimiento_caja_ruta.router)
app.include_router(ticket_ruta.router)
app.include_router(mobile_ruta.router)
app.include_router(upload_ruta.router)
app.include_router(seguridad_ruta.router)
app.include_router(citas_ruta.router)


@app.get("/")
def inicio():
    return {"mensaje": "API del Taller funcionando correctamente"}
