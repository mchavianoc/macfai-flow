#!/usr/bin/env bash
# Salir en caso de error
set -o errexit

# Instalar dependencias (si no lo hace Render automáticamente, pero lo incluimos por si acaso)
pip install -r requirements.txt

# Ejecutar migraciones de Django
python manage.py migrate --noinput

# Recopilar archivos estáticos
python manage.py collectstatic --noinput

# (Opcional) Crear superusuario si no existe (puedes omitir o ajustar)
# python manage.py createsuperuser --noinput --email admin@example.com || true