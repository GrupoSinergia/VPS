// Script para configurar credenciales Ollama en N8N
const http = require('http');

const options = {
  hostname: 'localhost',
  port: 5678,
  path: '/api/v1/credentials',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
};

const credentialData = {
  name: 'Ollama account',
  type: 'ollamaApi',
  data: {
    baseUrl: 'http://localhost:11434'
  }
};

const req = http.request(options, (res) => {
  let data = '';

  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('Status:', res.statusCode);
    console.log('Response:', data);
  });
});

req.on('error', (error) => {
  console.error('Error:', error);
});

req.write(JSON.stringify(credentialData));
req.end();