module.exports = {
  apps: [
    {
      name: "tt",
      script: "main.py",
      interpreter: "./.venv/bin/python",
      cwd: "./",
      instances: 1,
      autorestart: true,
      watch: false,
      env: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
      },
      error_file: "./logs/err.log",
      out_file: "./logs/out.log",
      log_file: "./logs/combined.log",
      time: true,
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      merge_logs: true,
      max_restarts: 10,
      restart_delay: 10000,
      ignore_watch: ["node_modules", "logs"],
      min_uptime: "10s",
    },
  ],
};
