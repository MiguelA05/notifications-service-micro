import os
from pathlib import Path

root = Path('.')
env_path = root / '.env'
backup_path = root / '.env.backup'
out_path = root / '.env.cleaned'

if not env_path.exists():
    raise SystemExit(".env not found")

# Read all lines
lines = env_path.read_text(encoding='utf-8', errors='ignore').splitlines()

pairs = []
for line in lines:
    s = line.strip()
    if not s or s.startswith('#'):
        pairs.append((None, line))  # preserve comments/blank for later optional merge
        continue
    if '=' not in line:
        # keep as-is
        pairs.append((None, line))
        continue
    key, val = line.split('=', 1)
    pairs.append((key.strip(), val))

# Keep last value per key
last_values = {}
for key, val in pairs:
    if key is None:
        continue
    last_values[key] = val

# Ensure required RabbitMQ vars for worker/scheduler
last_values.setdefault('RABBITMQ_HOST', 'rabbitmq')
last_values.setdefault('RABBITMQ_PORT', '5672')
last_values.setdefault('RABBITMQ_USERNAME', 'admin')
last_values.setdefault('RABBITMQ_PASSWORD', 'admin')
last_values.setdefault('AMQP_EXCHANGE', 'notifications.exchange')
last_values.setdefault('AMQP_QUEUE', 'notifications.queue')
last_values.setdefault('AMQP_ROUTING_KEY', 'notifications.key')

# Order keys by logical sections
sections = [
    ('# JWT Configuration', ['SECRET_KEY','ALGORITHM','ACCESS_TOKEN_EXPIRE_MINUTES']),
    ('# Database Configuration', ['DB_URL']),
    ('# RabbitMQ Configuration', ['RABBITMQ_HOST','RABBITMQ_PORT','RABBITMQ_USERNAME','RABBITMQ_PASSWORD','AMQP_EXCHANGE','AMQP_QUEUE','AMQP_ROUTING_KEY']),
    ('# Email Configuration', ['SMTP_USER','SMTP_PASSWORD','FROM_EMAIL','FROM_NAME','SENDGRID_API_KEY']),
    ('# Twilio Configuration', ['TWILIO_ACCOUNT_SID','TWILIO_AUTH_TOKEN','TWILIO_FROM_NUMBER','TWILIO_WHATSAPP_FROM','WHATSAPP_WEBHOOK_URL']),
    ('# Firebase Configuration', ['FIREBASE_PROJECT_ID','FIREBASE_SERVICE_ACCOUNT_KEY']),
    ('# Web Push Configuration', ['WEB_VAPID_PUBLIC_KEY','WEB_VAPID_PRIVATE_KEY']),
    ('# Worker Configuration', ['WORKER_MAX_RETRIES','WORKER_RETRY_DELAY_1','WORKER_RETRY_DELAY_2','WORKER_RETRY_DELAY_3','DEFAULT_CHANNEL']),
    ('# Scheduler Demo Configuration', ['SCHEDULER_DEMO_CHANNEL','SCHEDULER_DEMO_DESTINATION','SCHEDULER_DEMO_DELAY_SEC']),
]

lines_out = []
for title, keys in sections:
    lines_out.append(title)
    for k in keys:
        if k in last_values:
            lines_out.append(f"{k}={last_values[k]}")
    lines_out.append('')

out_path.write_text('\n'.join(lines_out), encoding='utf-8')

# Backup and replace
if backup_path.exists():
    backup_path.unlink()
env_path.rename(backup_path)
out_path.rename(env_path)
print('Cleaned .env written. Backup at .env.backup')
