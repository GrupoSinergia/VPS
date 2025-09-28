#!/bin/bash

echo "🔧 IMPORTANDO WORKFLOW DE N8N SIN CREDENCIALES"
echo "=============================================="
echo ""

# Verificar que n8n esté corriendo
if ! curl -s http://localhost:5678/healthz > /dev/null; then
    echo "❌ Error: n8n no está corriendo en localhost:5678"
    echo "   Ejecuta: sudo systemctl start n8n"
    exit 1
fi

# Verificar que Ollama esté corriendo
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Error: Ollama no está corriendo en localhost:11434"
    echo "   Ejecuta: ollama serve"
    exit 1
fi

echo "✅ n8n está corriendo en http://localhost:5678"
echo "✅ Ollama está corriendo en http://localhost:11434"
echo ""

echo "📋 PASOS PARA COMPLETAR LA CONFIGURACIÓN:"
echo "==========================================="
echo ""
echo "1. 🌐 Abre tu navegador en: http://localhost:5678"
echo ""
echo "2. 📥 Importa el workflow:"
echo "   - Ve a 'Workflows' > 'Import workflow'"
echo "   - Sube el archivo: n8n-complete-workflow.json"
echo ""
echo "3. 🔑 Configura las credenciales de Ollama:"
echo "   - Ve a 'Credentials' > 'Add Credential'"
echo "   - Busca y selecciona 'Ollama'"
echo "   - Nombre: 'Ollama account'"
echo "   - Base URL: 'http://localhost:11434'"
echo "   - Guarda las credenciales"
echo ""
echo "4. 🔗 Conecta las credenciales al workflow:"
echo "   - Abre el workflow importado"
echo "   - Haz clic en el nodo 'Ollama Chat Model'"
echo "   - En 'Credentials', selecciona 'Ollama account'"
echo "   - Guarda el workflow"
echo ""
echo "5. ▶️  Activa el workflow:"
echo "   - Toggle el switch 'Active' en la esquina superior"
echo ""
echo "6. 🧪 Prueba el webhook:"
echo "   - URL del webhook: http://localhost:5678/webhook/voip-agent"
echo "   - Método: POST"
echo "   - Body: {\"text\": \"Hola, quiero agendar una cita\"}"
echo ""
echo "🎯 COMANDO DE PRUEBA:"
echo "curl -X POST http://localhost:5678/webhook/voip-agent \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Hola, necesito información sobre sus servicios\"}'"
echo ""

# Verificar si el archivo de workflow existe
if [ -f "n8n-complete-workflow.json" ]; then
    echo "✅ Archivo de workflow encontrado: n8n-complete-workflow.json"
else
    echo "❌ Archivo de workflow no encontrado: n8n-complete-workflow.json"
    exit 1
fi

echo ""
echo "🚀 ¡Todo listo para importar el workflow!"