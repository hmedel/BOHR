# Servicios systemd de BOHR

Copias de referencia de los archivos de servicio instalados en `/etc/systemd/system/`.

## Instalación (en servidor nuevo)

```bash
sudo cp bohr-backend.service bohr-frontend.service bohr-backup.service /etc/systemd/system/
sudo cp logrotate.bohr /etc/logrotate.d/bohr
sudo systemctl daemon-reload
sudo systemctl enable bohr-backend bohr-frontend bohr-backup
sudo systemctl start bohr-backend bohr-frontend bohr-backup
```

## Gestión

```bash
sudo systemctl status bohr-backend bohr-frontend bohr-backup   # estado
sudo systemctl restart bohr-backend                            # tras cambios de código
sudo systemctl stop bohr-backend bohr-frontend bohr-backup     # detener todo
```

## Notas

- El backend usa el Python del entorno conda: `/home/medel/.julia/conda/3/x86_64/envs/bohrenv/bin/python`
- Los logs van a `logs/backend_production.log`, `logs/frontend_production.log` y `logs/backup.log`
- Requiere que Ollama esté corriendo (`ollama.service`) para los embeddings
- `bohr-backup` ejecuta backup semanal de la DB + rotación automática de logs
