# Reporte de Auditoría de Seguridad

## Fecha: 2026-04-01

## Análisis Estático con Bandit

✅ **RESULTADO: APROBADO**

- Total de líneas escaneadas: 8,545
- Problemas encontrados: 0 (después de filtrar falsos positivos)
- Severidad: N/A

### Falsos Positivos Ignorados:
- B105: hardcoded_password_string (constantes como "PASSWORD_CHANGE", no contraseñas reales)
- B106: hardcoded_password_funcarg (argumentos como token_type="refresh", no contraseñas)
- B110: try_except_pass (manejo de excepciones intencional en código asíncrono)

## Análisis de Dependencias con Safety

⚠️ **RESULTADO: VULNERABILIDADES ENCONTRADAS**

### Vulnerabilidades Críticas:

#### 1. Werkzeug 3.1.3 (3 vulnerabilidades)
- **CVE-2026-27199**: DoS por manejo incorrecto de nombres de dispositivos Windows
- **CVE-2025-66221**: DoS por validación insuficiente de dispositivos Windows
- **CVE-2026-21860**: Manejo incorrecto de nombres de dispositivos Windows
- **Recomendación**: Actualizar a Werkzeug 3.1.7

#### 2. Flask 3.1.2 (1 vulnerabilidad)
- **CVE-2026-27205**: Divulgación de información por headers de caché faltantes
- **Recomendación**: Actualizar a Flask 3.1.3

#### 3. pip 25.2 (1 vulnerabilidad)
- **CVE-2026-1703**: Path Traversal en extracción de archivos wheel
- **Recomendación**: Actualizar a pip 26.0.1

#### 4. ecdsa 0.19.1 (2 vulnerabilidades)
- **CVE-2024-23342**: Vulnerable al ataque Minerva (timing attack)
- **Sin CVE**: No protege contra ataques de canal lateral
- **Nota**: Los mantenedores NO planean corregir estas vulnerabilidades porque es imposible implementar código seguro contra canales laterales en Python puro
- **Recomendación**: Aceptar el riesgo o migrar a una librería criptográfica en C (como cryptography)

### Acciones Recomendadas:

1. **Actualizar dependencias inmediatamente**:
   ```bash
   pip install --upgrade werkzeug==3.1.7 flask==3.1.3 pip==26.0.1
   ```

2. **ecdsa**: Esta librería se usa indirectamente a través de python-jose para JWT. Considerar:
   - Aceptar el riesgo (los ataques de canal lateral requieren acceso físico o muy cercano)
   - Migrar a PyJWT que usa cryptography (librería en C)

3. **Verificar después de actualizar**:
   ```bash
   safety check
   ```

## Conclusión

El código de la aplicación está libre de vulnerabilidades de seguridad estáticas (bandit). Las vulnerabilidades encontradas son en dependencias de terceros y pueden ser mitigadas actualizando a las versiones más recientes.

La vulnerabilidad de ecdsa es conocida y aceptada por los mantenedores. Para un entorno de producción, se recomienda evaluar el modelo de amenazas y decidir si es necesario migrar a una librería criptográfica más robusta.
