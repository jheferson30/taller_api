#!/usr/bin/env python3
"""
Script auxiliar para generar el hash bcrypt de una contraseña.

Uso:
    python scripts/generar_hash_bcrypt.py

El hash generado debe copiarse en scripts/crear_super_admin.sql
como valor de la variable v_password_hash.

Requisitos:
    pip install passlib[bcrypt]
    (ya incluido en requirements.txt del proyecto)
"""
import getpass
import sys


def generar_hash(password: str) -> str:
    """Genera un hash bcrypt con costo 12."""
    try:
        from passlib.context import CryptContext
    except ImportError:
        print("❌ Error: passlib no está instalado.")
        print("   Ejecutar: pip install passlib[bcrypt]")
        sys.exit(1)

    ctx = CryptContext(schemes=["bcrypt"], bcrypt__rounds=12)
    return ctx.hash(password)


def validar_fortaleza(password: str) -> list[str]:
    """Valida que la contraseña cumpla requisitos mínimos de seguridad."""
    errores = []
    if len(password) < 12:
        errores.append("Debe tener al menos 12 caracteres")
    if not any(c.isupper() for c in password):
        errores.append("Debe contener al menos una letra mayúscula")
    if not any(c.islower() for c in password):
        errores.append("Debe contener al menos una letra minúscula")
    if not any(c.isdigit() for c in password):
        errores.append("Debe contener al menos un número")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errores.append("Debe contener al menos un carácter especial")
    return errores


def main():
    print("=" * 60)
    print("  Generador de Hash Bcrypt para SUPER_ADMIN")
    print("=" * 60)
    print()
    print("⚠️  Esta contraseña se usará para el usuario SUPER_ADMIN.")
    print("   Guárdala en un gestor de contraseñas seguro.")
    print()

    # Solicitar contraseña de forma segura (sin eco en terminal)
    while True:
        password = getpass.getpass("Ingresa la contraseña: ")
        confirmacion = getpass.getpass("Confirma la contraseña: ")

        if password != confirmacion:
            print("❌ Las contraseñas no coinciden. Intenta de nuevo.\n")
            continue

        errores = validar_fortaleza(password)
        if errores:
            print("❌ La contraseña no cumple los requisitos:")
            for error in errores:
                print(f"   - {error}")
            print()
            continuar = input("¿Continuar de todas formas? (s/N): ").strip().lower()
            if continuar != "s":
                continue

        break

    print()
    print("⏳ Generando hash bcrypt (costo 12)...")
    hash_resultado = generar_hash(password)

    print()
    print("=" * 60)
    print("✅ Hash generado exitosamente:")
    print()
    print(hash_resultado)
    print()
    print("=" * 60)
    print()
    print("📋 Instrucciones:")
    print("   1. Copiar el hash de arriba.")
    print("   2. Abrir scripts/crear_super_admin.sql")
    print("   3. Reemplazar el valor de v_password_hash con el hash.")
    print("   4. Ejecutar:")
    print("      psql -U postgres -d taller_v3 -f scripts/crear_super_admin.sql")
    print()
    print("⚠️  No guardar este hash en el historial del terminal.")
    print("   Considera limpiar el historial: history -c")


if __name__ == "__main__":
    main()
