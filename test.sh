# 1) Crear la invoice y capturar la respuesta JSON
resp=$(curl -s -X POST http://localhost:8000/invoices/ \
  -H "x-api-key: test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_hash":"hash-nuevo-123",
    "amount_msat":100000,
    "description":"Prueba generación de PDF"
  }')

echo "Respuesta: $resp"

# 2) Extraer el receipt_id (requiere jq)
receipt_id=$(echo "$resp" | jq -r .receipt_id)
echo "receipt_id = $receipt_id"

# 3) Descargar el PDF
curl -v -H "x-api-key: test-key-123" \
  http://localhost:8000/receipts/"$receipt_id" \
  --output recibo.pdf

echo "📄 PDF descargado en recibo.pdf"
