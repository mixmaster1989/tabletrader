# Настройка Google Credentials

## Отсутствующие файлы:
1. `credentials.json` - файл с учетными данными Google API
2. `token.pickle` - файл с токеном авторизации (создается автоматически)

## Пошаговая настройка credentials.json:

### 1. Создание проекта в Google Cloud Console
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Запомните ID проекта

### 2. Включение Google Sheets API
1. В меню слева выберите "APIs & Services" > "Library"
2. Найдите "Google Sheets API"
3. Нажмите "Enable"

### 3. Создание Service Account
1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните форму:
   - **Name**: `tabletrader-bot` (или любое имя)
   - **Description**: `Service account for TableTrader bot`
4. Нажмите "Create and Continue"
5. Пропустите "Grant this service account access to project" (нажмите "Done")

### 4. Создание ключа
1. В списке Service Accounts найдите созданный аккаунт
2. Нажмите на email аккаунта
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите "JSON"
6. Нажмите "Create"
7. Файл автоматически скачается

### 5. Настройка файла
1. Переименуйте скачанный файл в `credentials.json`
2. Поместите его в корневую папку проекта (где `main.py`)

### 6. Предоставление доступа к таблице
1. Откройте вашу Google таблицу
2. Нажмите "Share" (в правом верхнем углу)
3. Добавьте email из `credentials.json` (найдите поле `client_email`)
4. Дайте права "Editor"
5. Нажмите "Send"

## Проверка настройки:
```bash
python test_google_setup.py
```

## Структура credentials.json:
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "tabletrader-bot@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

## Важные замечания:
- **Безопасность**: Не публикуйте `credentials.json` в git
- **Права доступа**: Service Account должен иметь доступ к таблице
- **API квоты**: Убедитесь, что Google Sheets API включен
- **token.pickle**: Создается автоматически при первом запуске 