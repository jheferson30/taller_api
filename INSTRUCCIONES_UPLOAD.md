# Sistema de Carga de Archivos Implementado

## ✅ Funcionalidades Agregadas

1. **Subir fotos de evidencia** desde el equipo
2. **Subir soportes de compras** (facturas, recibos) desde el equipo
3. **Preview de imágenes** antes de subir
4. **Opción dual**: Subir archivo O pegar URL

## Cómo Usar

### 1. Reiniciar Backend y Frontend

```bash
# Backend
uvicorn app.main:app --reload

# Frontend (en otra terminal)
cd frontend
npm run dev
```

### 2. Subir Fotos de Evidencia

1. Ve a **Tickets** → Selecciona un ticket → Tab **Fotos**
2. Verás dos opciones:
   - **Subir Foto desde el Equipo**: Click en "Elegir archivo" → Selecciona imagen → Verás preview
   - **O pegar URL**: Si prefieres usar una URL externa
3. Agrega descripción y tipo (Antes/Después/Otra)
4. Click en "Agregar Foto"

### 3. Subir Soportes de Compras

1. Ve a **Tickets** → Selecciona un ticket → Tab **Compras**
2. Llena descripción y valor
3. Verás dos opciones:
   - **Subir Soporte**: Click en "Elegir archivo" → Selecciona imagen o PDF
   - **O pegar URL**: Si prefieres usar una URL externa
4. Click en "Registrar Compra"

## Estructura de Archivos

Los archivos se guardan en:
```
taller_api/
├── uploads/
│   ├── fotos/          # Fotos de evidencia
│   ├── compras/        # Soportes de compras
│   └── firmas/         # Firmas de entrega
```

## Características Técnicas

- **Formatos permitidos**: JPG, JPEG, PNG, GIF, WEBP, PDF
- **Tamaño máximo**: 10MB por archivo
- **Nombres únicos**: Se generan automáticamente (timestamp + UUID)
- **URLs generadas**: `http://127.0.0.1:8000/uploads/fotos/20260311_abc123.jpg`

## Endpoints Nuevos

- `POST /upload/foto` - Subir foto de evidencia
- `POST /upload/compra` - Subir soporte de compra
- `POST /upload/firma` - Subir firma de entrega
- `GET /uploads/fotos/{filename}` - Ver foto
- `GET /uploads/compras/{filename}` - Ver soporte
- `GET /uploads/firmas/{filename}` - Ver firma

## Ventajas

✅ No requiere servicios externos (AWS S3, Cloudinary, etc.)
✅ Sin costos adicionales
✅ Archivos almacenados localmente
✅ Preview de imágenes antes de subir
✅ Validación de formato y tamaño
✅ Nombres únicos para evitar conflictos

## Migración Futura a la Nube (Opcional)

Si en el futuro quieres migrar a AWS S3 o Cloudinary:
1. Solo cambias la función de upload en `upload_ruta.py`
2. El resto del código sigue igual
3. Las URLs cambiarían de local a cloud

## Notas Importantes

- La carpeta `uploads/` se crea automáticamente
- Los archivos NO se eliminan automáticamente (puedes implementar limpieza manual)
- Asegúrate de hacer backup de la carpeta `uploads/` regularmente
- En producción, considera usar un servidor de archivos dedicado
