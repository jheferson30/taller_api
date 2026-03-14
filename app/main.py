from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

load_dotenv()

from app.configuracion.base_datos import Base, engine
from app.rutas import economia_ruta, movimiento_caja_ruta, ticket_ruta, upload_ruta, vehiculo_ruta, seguridad_ruta, citas_ruta, mobile_api_ruta
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
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(vehiculo_ruta.router)
app.include_router(economia_ruta.router)
app.include_router(movimiento_caja_ruta.router)
app.include_router(ticket_ruta.router)
app.include_router(ticket_ruta.router_pdf)
app.include_router(upload_ruta.router)
app.include_router(seguridad_ruta.router)
app.include_router(citas_ruta.router)
app.include_router(mobile_api_ruta.router)


@app.on_event("startup")
def validar_variables_entorno():
    if not os.getenv("PDF_PASSWORD"):
        raise RuntimeError("PDF_PASSWORD env var is required")
    if not os.getenv("ADMIN_PASSWORD") and not os.getenv("PDF_PASSWORD"):
        raise RuntimeError("ADMIN_PASSWORD env var is required")


@app.get("/")
def inicio():
    return {"mensaje": "API del Taller funcionando correctamente"}
