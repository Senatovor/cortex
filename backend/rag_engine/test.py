import requests
import json

response = requests.get('http://10.11.12.64:11434/api/tags')
print(json.dumps(response.json(), indent=2, ensure_ascii=False))


# Быстрая проверка через REST API
response = requests.post(
    'http://10.11.12.64:11434/api/generate',
    json={
        'model': 'rnj-1-instruct-Q4_K_M:latest',
        'prompt': 'Напиши приветствие на русском языке',
        'stream': False
    }
)

print("Статус код:", response.status_code)
print("Ответ от модели:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
