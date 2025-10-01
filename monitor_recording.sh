#!/bin/bash

###############################################################################
# SCRIPT DE MONITOREO DE GRABACIONES
# Verifica que channel.record() cree archivos correctamente
###############################################################################

RECORDING_DIR="/var/spool/asterisk/recording"
WATCH_PATTERN="realtime_*.slin"

echo "========================================"
echo "MONITOR DE GRABACIONES - Asterisk ARI"
echo "========================================"
echo ""
echo "Directorio: $RECORDING_DIR"
echo "Patrón: $WATCH_PATTERN"
echo "Timestamp: $(date)"
echo ""

# Función para verificar archivos nuevos
check_new_files() {
    local current_count=$(ls -1 $RECORDING_DIR/$WATCH_PATTERN 2>/dev/null | wc -l)
    echo "Archivos realtime_*.slin actuales: $current_count"

    if [ $current_count -gt 0 ]; then
        echo ""
        echo "Últimos 5 archivos creados:"
        ls -lht $RECORDING_DIR/$WATCH_PATTERN 2>/dev/null | head -5

        # Verificar archivos con contenido
        echo ""
        echo "Archivos NO VACÍOS (>0 bytes):"
        find $RECORDING_DIR -name "$WATCH_PATTERN" -type f -size +0 -ls 2>/dev/null | wc -l

        # Verificar archivos vacíos (problema)
        local empty_count=$(find $RECORDING_DIR -name "$WATCH_PATTERN" -type f -size 0 2>/dev/null | wc -l)
        echo "Archivos VACÍOS (0 bytes): $empty_count"

        if [ $empty_count -gt 0 ]; then
            echo ""
            echo "⚠️  ADVERTENCIA: Hay archivos vacíos. Esto puede indicar un problema."
        fi
    else
        echo "No se encontraron archivos realtime_*.slin"
        echo ""
        echo "Esperando primera llamada para verificar la corrección..."
    fi
}

# Modo de monitoreo continuo
if [ "$1" == "--watch" ]; then
    echo "Modo WATCH activado. Monitoreando cada 5 segundos..."
    echo "Presiona Ctrl+C para detener."
    echo ""

    while true; do
        clear
        echo "========================================"
        echo "MONITOR DE GRABACIONES - $(date +%H:%M:%S)"
        echo "========================================"
        echo ""
        check_new_files
        sleep 5
    done
else
    check_new_files
    echo ""
    echo "Para monitoreo continuo, ejecuta: $0 --watch"
fi

echo ""
echo "========================================"
