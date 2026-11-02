# SOC Jira Automation V4

Automation ini memproses tiket **SIEM Alert** dari Jira, mengambil detail alert dari Elastic Security, menyamarkan data sensitif sebelum dikirim ke Gemini, memperbarui hasil analisis di Jira, menjalankan transisi workflow, serta mengirim notifikasi Telegram.

## Fitur utama

- Polling Jira setiap 30 detik dengan JQL terkonfigurasi.
- Assign atau re-assign tiket ke akun automation.
- Pemrosesan paralel menggunakan beberapa AI worker.
- Pengambilan `Alert_ID` langsung dari `customfield_10771`.
- `Alert Link` pada `customfield_10786` sebagai fallback.
- Retry pembacaan custom field jika Jira belum selesai melakukan sinkronisasi.
- Rotasi otomatis model Gemini berdasarkan availability, allowlist, rate limit, dan cooldown.
- Sanitasi terstruktur untuk identitas host, user, agent, event ID, URL internal, IP, email, MAC address, UUID, serta hash sensitif.
- Penyimpanan audit raw JSON dan sanitized JSON secara lokal.
- Logging terminal yang informatif dan rotating log file.
- Graceful shutdown ketika menerima `Ctrl+C`.

## Workflow tiket

### Tiket berstatus Open

```text
Open
  -> assign/re-assign
  -> L1 Analysis
  -> Waiting for User Confirmation
  -> AI analysis
```

### Tiket berstatus L1 Analysis

```text
L1 Analysis
  -> assign/re-assign
  -> Waiting for User Confirmation
  -> AI analysis
```

### Tiket berstatus Waiting for User Confirmation

```text
Waiting for User Confirmation
  -> assign/re-assign
  -> AI analysis
```

### Hasil analisis

```text
False Positive
  -> False Incident
  -> Done
  -> close alert Elastic
  -> Telegram notification
```

```text
Bukan False Positive
  -> tetap Waiting for User Confirmation
  -> Telegram notification
```

## Struktur proyek

```text
soc-automation/
├── main.py
├── config.py
├── jira_client.py
├── siem_client.py
├── prompt_builder.py
├── ticket_processor.py
├── worker_manager.py
├── gemini_manager.py
├── telegram_notifier.py
├── data_sanitizer.py
├── requirements.txt
├── env.example
├── .env
├── logs/
└── audit_logs/
```

## Persyaratan

- Python 3.10 atau lebih baru.
- Akses internet ke Jira Cloud, Elastic/Kibana, Gemini API, dan Telegram API.
- Jira API token dan Atlassian account ID.
- Elastic API key dengan permission membaca dan memperbarui alert.
- Gemini API key.
- Telegram bot token dan chat ID.
- Workflow Jira yang menyediakan transisi yang diperlukan.

## Instalasi umum

### 1. Masuk ke direktori proyek

```bash
cd /path/to/soc-automation
```

### 2. Buat virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Perbarui pip dan instal dependency

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Buat file konfigurasi

```bash
cp env.example .env
```

Buka `.env` dan ganti seluruh placeholder credential:

```bash
nano .env
```

Jangan menggunakan credential contoh pada environment production.

### 5. Buat secret sanitizer

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Salin hasilnya ke:

```dotenv
HASH_SECRET_KEY=hasil-random-secret
```

### 6. Periksa syntax seluruh module

```bash
python -m py_compile *.py
```

Jika tidak ada output, pemeriksaan syntax berhasil.

### 7. Jalankan automation

```bash
python main.py
```

## Instalasi di Termux

### 1. Persiapkan Termux

```bash
pkg update
pkg upgrade
pkg install python git unzip
termux-setup-storage
```

Setujui permission storage saat diminta.

### 2. Masuk ke folder proyek

```bash
cd ~/storage/Automation/V4
```

### 3. Instal dependency

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Siapkan `.env`

```bash
cp env.example .env
nano .env
```

### 5. Periksa dan jalankan

```bash
python -m py_compile *.py
python main.py
```

Agar Android tidak langsung menghentikan Termux ketika layar mati:

```bash
termux-wake-lock
```

Setelah automation dihentikan:

```bash
termux-wake-unlock
```

Disarankan juga menonaktifkan battery optimization untuk Termux melalui pengaturan Android.

## Konfigurasi `.env`

Gunakan `env.example` sebagai referensi lengkap. Bagian pentingnya dijelaskan berikut.

### Jira

```dotenv
JIRA_DOMAIN=bankjasajakarta
JIRA_EMAIL=analyst@example.com
JIRA_API_TOKEN=replace-with-jira-token
JIRA_ACCOUNT_ID=replace-with-atlassian-account-id
JIRA_PROJECT_KEY=CSOC
JIRA_ISSUE_TYPE=SIEM Alert

JIRA_ALERT_ID_FIELD_ID=customfield_10771
JIRA_ALERT_LINK_FIELD_ID=customfield_10786
JIRA_ANALYSIS_FIELD_ID=customfield_10798

JIRA_STATUS_OPEN=Open
JIRA_STATUS_L1_ANALYSIS=L1 Analysis
JIRA_STATUS_WAITING_CONFIRMATION=Waiting for User Confirmation
JIRA_STATUS_FALSE_INCIDENT=False Incident
JIRA_STATUS_DONE=Done
JIRA_REQUEST_TIMEOUT=30
```

`customfield_10771` diperlakukan sebagai sumber Alert ID utama. Selama field tersebut terisi, nilainya digunakan langsung tanpa pembatasan panjang atau format hexadecimal.

### Elastic SIEM

```dotenv
SIEM_API_BASE_URL=https://your-deployment.example
ELASTIC_API_KEY=replace-with-elastic-api-key
SIEM_REQUEST_TIMEOUT=30
SIEM_VERIFY_SSL=true
```

Gunakan `SIEM_VERIFY_SSL=true` jika sertifikat dapat diverifikasi. Gunakan `false` hanya jika benar-benar diperlukan oleh environment internal.

### Gemini dan rotasi model

```dotenv
GEMINI_API_KEY=replace-with-gemini-api-key
AI_MAX_WORKERS=3
GEMINI_ALLOWED_MODELS=gemini-3.5-flash,gemini-3.1-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite,gemini-2.0-flash,gemini-2.0-flash-lite,gemini-2.5-pro
GEMINI_MAX_CYCLES=2
GEMINI_REQUEST_DELAY_SECONDS=2.5
GEMINI_CYCLE_DELAY_SECONDS=60
GEMINI_MODEL_CACHE_SECONDS=900
GEMINI_RATE_LIMIT_COOLDOWN_SECONDS=60
GEMINI_ERROR_COOLDOWN_SECONDS=30
```

Automation mengambil daftar model yang tersedia pada API key, memilih model yang mendukung `generateContent`, mencocokkannya dengan `GEMINI_ALLOWED_MODELS`, kemudian merotasi model sesuai urutan konfigurasi. Model yang terkena rate limit akan masuk cooldown bersama untuk seluruh AI worker.

### Polling dan retry Jira

```dotenv
POLL_INTERVAL_SECONDS=30
MAX_SEARCH_RESULTS=100
SHUTDOWN_WAIT_FOR_WORKERS=true
JIRA_ALERT_FIELD_MAX_ATTEMPTS=5
JIRA_ALERT_FIELD_RETRY_SECONDS=3
```

- Poller Jira berjalan setiap 30 detik.
- Retry Alert ID hanya menahan worker tiket terkait, bukan poller utama.
- Jika `Alert_ID` tersedia pada percobaan pertama, worker tidak menunggu retry berikutnya.

### Telegram

```dotenv
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=replace-with-telegram-bot-token
TELEGRAM_CHAT_ID=replace-with-telegram-chat-id
TELEGRAM_REQUEST_TIMEOUT=15
```

Untuk menonaktifkan Telegram sementara:

```dotenv
TELEGRAM_ENABLED=false
```

### Sanitizer dan audit

```dotenv
HASH_SECRET_KEY=replace-with-long-random-hmac-secret
HASH_LENGTH=12
AUDIT_DIR=audit_logs
```

Sanitizer mempertahankan konteks keamanan penting seperti nama process, executable path, registry path, signature trust, nama rule, severity, MITRE ATT&CK, dan timestamp. Identifier sensitif dipseudonymkan sebelum payload dikirim ke Gemini.

### Logging

```dotenv
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_FILE=logs/soc_automation.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5
```

Pilihan level:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Untuk operasional normal, gunakan `INFO`. Untuk troubleshooting sementara, gunakan `DEBUG`.

## Menjalankan sebagai background process

### Menggunakan `nohup`

```bash
nohup python main.py > automation.out 2>&1 &
```

Lihat output:

```bash
tail -f automation.out
```

Cari process:

```bash
pgrep -af "python main.py"
```

Hentikan process:

```bash
pkill -f "python main.py"
```

Untuk penggunaan jangka panjang, lebih disarankan menggunakan systemd, supervisor, Docker, atau process manager lain dibanding hanya `nohup`.

## Menghentikan automation

Jika automation berjalan di foreground:

```text
Ctrl+C
```

Automation akan menghentikan polling, menangani worker sesuai `SHUTDOWN_WAIT_FOR_WORKERS`, lalu menutup session Jira, SIEM, dan Telegram.

## Verifikasi koneksi dan konfigurasi

### Periksa environment wajib tanpa mencetak secret

```bash
python - <<'PY'
from dotenv import load_dotenv
import os

load_dotenv()

required = [
    "JIRA_EMAIL",
    "JIRA_API_TOKEN",
    "JIRA_ACCOUNT_ID",
    "ELASTIC_API_KEY",
    "GEMINI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "HASH_SECRET_KEY",
]

for name in required:
    status = "OK" if os.getenv(name, "").strip() else "MISSING"
    print(f"{name}: {status}")
PY
```

### Periksa custom field Alert ID

```bash
python - <<'PY'
from jira_client import JiraClient

TICKET_KEY = "CSOC-XXXXX"

with JiraClient() as jira:
    issue = jira.get_issue(
        TICKET_KEY,
        fields=["customfield_10771", "customfield_10786"],
    )

fields = issue.get("fields", {})
alert_id = fields.get("customfield_10771")
alert_link = fields.get("customfield_10786")

print("Alert_ID tersedia :", bool(alert_id))
print("Alert Link tersedia:", bool(alert_link))
print("Panjang Alert_ID   :", len(str(alert_id or "").strip()))
PY
```

### Uji Telegram

```bash
python - <<'PY'
from telegram_notifier import kirim_notifikasi_telegram

sent = kirim_notifikasi_telegram(
    "<b>Test</b> SOC Automation berhasil terhubung ke Telegram."
)
print("Terkirim:", sent)
PY
```

### Lihat model Gemini yang masuk rotasi

```bash
python - <<'PY'
from google import genai
from config import settings
from gemini_manager import dapatkan_model_dinamis

client = genai.Client(api_key=settings.gemini.api_key)
models = dapatkan_model_dinamis(client)

for model in models:
    print(model)
PY
```

## Logging dan monitoring

Pada startup, terminal akan menampilkan konfigurasi utama:

```text
SOC AUTOMATION AKTIF
Workflow : Open -> L1 Analysis -> Waiting for User Confirmation
Runtime  : 3 AI worker | cek setiap 30 detik
```

Heartbeat polling:

```text
[CHECK #0001] Memeriksa seluruh tiket hasil JQL...
[CHECK #0001] Ringkasan status — Open: 1 | Waiting for User Confirmation: 3
[CHECK #0001] Selesai ... Cek berikutnya dalam 30 detik.
```

Log file default:

```text
logs/soc_automation.log
```

Pantau log:

```bash
tail -f logs/soc_automation.log
```

## Audit dan keamanan data

Automation menyimpan:

```text
audit_logs/CSOC-XXXXX_raw.json
audit_logs/CSOC-XXXXX_sanitized.json
audit_logs/hash_audit_YYYY-MM-DD.csv
```

`raw.json` dan file mapping CSV mengandung data sensitif. Lindungi aksesnya:

```bash
chmod 700 audit_logs
chmod 600 audit_logs/*
```

Tambahkan ke `.gitignore`:

```gitignore
.env
logs/
audit_logs/
__pycache__/
*.py[cod]
.venv/
```

Jangan commit atau membagikan:

- `.env`
- Jira API token
- Elastic API key
- Gemini API key
- Telegram bot token
- `HASH_SECRET_KEY`
- raw audit JSON
- hash audit mapping CSV

## Troubleshooting

### `ConfigurationError: HASH_SECRET_KEY`

Tambahkan secret ke `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

```dotenv
HASH_SECRET_KEY=hasil-random-secret
```

### Polling masih 10 detik

Periksa `.env`:

```bash
grep '^POLL_INTERVAL_SECONDS=' .env
```

Nilai yang diharapkan:

```dotenv
POLL_INTERVAL_SECONDS=30
```

Restart aplikasi setelah mengubah `.env`.

### `missing_alert_id`

Periksa:

```dotenv
JIRA_ALERT_ID_FIELD_ID=customfield_10771
JIRA_ALERT_LINK_FIELD_ID=customfield_10786
JIRA_ALERT_FIELD_MAX_ATTEMPTS=5
JIRA_ALERT_FIELD_RETRY_SECONDS=3
```

Pastikan akun Jira API memiliki permission membaca kedua custom field tersebut.

### Jira transition tidak tersedia

Pastikan workflow Jira mengizinkan:

```text
Open -> L1 Analysis
L1 Analysis -> Waiting for User Confirmation
Waiting for User Confirmation -> False Incident
False Incident -> Done
```

Nama status pada `.env` harus sama dengan nama status Jira.

### Gemini terkena rate limit

Automation otomatis memindahkan model tersebut ke cooldown dan mencoba model berikutnya. Jika seluruh model limit:

- kurangi `AI_MAX_WORKERS`;
- naikkan `GEMINI_REQUEST_DELAY_SECONDS`;
- naikkan `GEMINI_RATE_LIMIT_COOLDOWN_SECONDS`;
- periksa quota project Gemini.

### Telegram tidak terkirim

Periksa:

- `TELEGRAM_ENABLED=true`;
- bot token valid;
- chat ID benar;
- bot sudah memiliki akses ke chat atau group;
- koneksi jaringan tidak memblokir Telegram API.

### SIEM alert tidak ditemukan

Pastikan:

- nilai `Alert_ID` pada Jira sesuai dengan `_id` alert Elastic;
- Elastic API key memiliki permission pencarian alert;
- `SIEM_API_BASE_URL` benar;
- custom field Jira tidak berisi URL penuh jika field tersebut seharusnya hanya berisi ID.

## Update aplikasi

Sebelum mengganti versi:

```bash
cp .env ../.env.backup
cp -r audit_logs ../audit_logs.backup
```

Setelah file baru diekstrak:

```bash
cp ../.env.backup .env
pip install -r requirements.txt
python -m py_compile *.py
python main.py
```

Jangan menimpa `.env` production menggunakan `env.example`.

## Checklist sebelum production

- [ ] Semua credential pada `.env` sudah diisi.
- [ ] `.env` tidak masuk version control.
- [ ] Jira custom field IDs sudah benar.
- [ ] Nama status sama dengan workflow Jira.
- [ ] Elastic API key dapat mencari dan menutup alert.
- [ ] Gemini API key dapat mengakses model allowlist.
- [ ] Telegram test message berhasil.
- [ ] `POLL_INTERVAL_SECONDS=30`.
- [ ] `HASH_SECRET_KEY` menggunakan random secret yang kuat.
- [ ] Permission `logs/` dan `audit_logs/` sudah dibatasi.
- [ ] Syntax check berhasil.
- [ ] Satu tiket pengujian berhasil diproses end-to-end.


## Privacy discovery dan fail-closed gate

Sebelum payload dikirim ke Gemini, automation menjalankan pipeline lokal:

```text
SIEM JSON -> sensitive-data discovery -> consistent replacement map
-> recursive sanitization -> global free-text replacement -> residual scan
-> PASS: Gemini | BLOCK: Telegram error dan tetap Waiting
```

Detector memprioritaskan path terstruktur seperti host, user, agent, event,
process entity, ancestor, internal index/URL, serta pola IP, email, MAC, profile
Windows, UNC host, dan token-like values. Data analitis seperti process name,
command line, registry, code-signature trust/vendor, rule name, severity, MITRE,
dan timestamp dipertahankan. Sistem bersifat fail closed: payload tidak dikirim
ke Gemini jika residual high-confidence sensitive data masih ditemukan.

Tidak ada detector generik yang dapat memberikan jaminan matematis 100% terhadap
semua format sensitif yang belum pernah didefinisikan. Privacy gate memberikan
jaminan operasional terkuat: semua temuan detector harus hilang sebelum payload
dikirim, dan format baru yang belum dikenali harus ditambahkan sebagai rule/test.


### UNC path dan registry/EQL preservation

Privacy detector hanya menganggap pola `\\server\share` yang jelas sebagai UNC path.
Escape sequence pada EQL, registry path, dan Windows path tidak dianggap sebagai hostname.
Kata teknis seperti `Services`, `NetworkProvider`, `System32`, `REGISTRY`, dan
`MACHINE` dipertahankan karena diperlukan untuk analisis alert.

Contoh yang dipertahankan:

```text
\REGISTRY\MACHINE
HKLM\SYSTEM\ControlSet001\Services\...\NetworkProvider\ProviderPath
%SystemRoot%\System32\ntlanman.dll
```

Contoh UNC asli yang disanitasi:

```text
\\fileserver01\finance\report.csv
-> \\HOST_<pseudonym>\finance\report.csv
```
