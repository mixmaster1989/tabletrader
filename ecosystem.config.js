module.exports = {
  apps: [{
    name: 'tabletrader-bot',
    script: 'main.py',
    interpreter: 'python3',
    cwd: './',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    // Автоматический перезапуск при сбоях
    max_restarts: 10,
    min_uptime: '10s',
    // Перезапуск при изменении файлов (опционально)
    watch: [
      'main.py',
      'config.py',
      'bybit_api.py',
      'google_sheets_api.py',
      'signal_processor.py',
      'telegram_bot.py'
    ],
    ignore_watch: [
      'node_modules',
      'logs',
      '.env',
      '__pycache__',
      '*.pyc'
    ]
  }]
}; 