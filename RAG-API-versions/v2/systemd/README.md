# Servicios systemd de BOHR

Copias de referencia de los archivos de servicio instalados en `/etc/systemd/system/`.

## Instalación (en servidor nuevo)

```bash
sudo cp bohr-backend.service bohr-frontend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bohr-backend bohr-frontend
sudo systemctl start bohr-backend bohr-frontend
```

## Gestión

```bash
sudo systemctl status bohr-backend bohr-frontend   # estado
sudo systemctl restart bohr-backend                # tras cambios de código
sudo systemctl stop bohr-backend bohr-frontend     # detener
```

## Notas

- El backend usa el Python del entorno conda: `/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python`
- Los logs van a `logs/backend_production.log` y `logs/frontend_production.log`
- Requiere que Ollama esté corriendo (`ollama.service`) para los embeddings
