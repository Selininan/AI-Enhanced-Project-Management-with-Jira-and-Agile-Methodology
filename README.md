
# AI-Enhanced Project Management with Jira and Agile Methodology

**İstinye Üniversitesi — Capstone Project**
**Öğrenciler:** Selin İnan / Zeynep Uzun
**Danışman:** Alper Öner

---

## 📌 Proje Hakkında

Bu proje, Beko çalışanlarının kullandığı Jira ortamına entegre edilmiş bir **AI Agent sistemidir**. Sistem, Jira'daki sprint verilerini gerçek zamanlı olarak analiz ederek proje yöneticilerine otomatik risk değerlendirmesi, kapasite analizi ve akıllı görev önerileri sunar.

---

## 🏗️ Sistem Mimarisi

```
Jira (BAI Projesi)
        ↓  REST API
   main.py / fastapi_server.py
        ↓
   ┌─────────────────────────────┐
   │         AI Agents           │
   │  • risk_agent               │
   │  • capacity_agent           │
   │  • recommendation_agent     │
   │  • requirement_agent        │
   │  • task_validation_agent    │
   │  • jira_support_agent       │
   └─────────────────────────────┘
        ↓
   FastAPI Endpoints
   /health | /analyze/sprint | /analyze/capacity | /support/ask
        ↓
   PDF Report + CSV Dataset + Risk Chart
```

---

## 🤖 AI Agentlar

| Agent | Görev |
|-------|-------|
| `risk_agent` | Her task için gecikme, öncelik, statü ve belirsizlik faktörlerine göre risk skoru hesaplar |
| `capacity_agent` | Takım uzmanlıklarını dinamik olarak öğrenerek kapasite vs iş yükü karşılaştırması yapar |
| `recommendation_agent` | Kişi-uzmanlık eşleşmesini öğrenir, yanlış atama ve gecikme uyarısı verir |
| `requirement_agent` | PMI standartlarına göre Aktör ve Kabul Kriteri kontrolü yapar |
| `task_validation_agent` | Summary, description, assignee, epic ve priority alanlarını doğrular |
| `jira_support_agent` | Jira ile ilgili sorulara rehber tabanlı cevap verir |

---

## 🚀 Kurulum

### 1. Repoyu klonla
```bash
git clone https://github.com/kullanici/AI-Enhanced-Project-Management.git
cd AI-Enhanced-Project-Management
```

### 2. Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```

### 3. `.env` dosyasını oluştur
Repo kökünde `.env` dosyası oluştur ve aşağıdaki değerleri doldur:
```
JIRA_EMAIL=your-email@beko.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_DOMAIN=your-domain.atlassian.net
JIRA_PROJECT_KEY=BAI
ANTHROPIC_API_KEY=your-anthropic-api-key
```

> ⚠️ `.env` dosyası `.gitignore`'a eklidir, GitHub'a gitmez.

---

## ▶️ Kullanım

### Tam analiz çalıştır (terminal çıktısı + CSV + PDF + Jira comment)
```bash
python main.py
```

### FastAPI sunucusunu başlat
```bash
uvicorn fastapi_server:app --reload --port 8000
```

Swagger UI ile endpoint'leri test et:
```
http://127.0.0.1:8000/docs
```

---

## 🌐 API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | `/health` | Sistem durumu kontrolü |
| POST | `/analyze/sprint` | Sprint risk raporu, gecikme ve öneriler |
| POST | `/analyze/capacity` | Kapasite vs iş yükü analizi |
| POST | `/support/ask` | Jira destek sorusu cevabı |

### Örnek: `/support/ask`
```json
POST /support/ask
{
  "question": "What is the difference between a story and a task?"
}
```

---

## 📁 Klasör Yapısı

```
├── agents/
│   ├── capacity_agent.py
│   ├── jira_support_agent.py
│   ├── recommendation_agent.py
│   ├── requirement_agent.py
│   ├── risk_agent.py
│   └── task_validation_agent.py
├── context/
│   └── context_builder.py
├── reports/
│   └── pdf_report.py
├── fastapi_server.py
├── main.py
├── jira_guide.txt
├── requirements.txt
└── .env  ← (gitignore'da, GitHub'a gitmez)
```

---

## 📊 Üretilen Çıktılar

- `jira_dataset.csv` — Tüm Jira verisi + AI analiz kolonları
- `validation_report.csv` — Task doğrulama sonuçları
- `sprint_report.pdf` — Yüksek riskli taskların PDF raporu
- `risk_chart.png` — Task bazlı risk skoru grafiği
- Jira Comments — Problem tasklar için otomatik yorum

---

## 🔧 Gereksinimler

```
requests
pandas
matplotlib
fpdf
python-dotenv
fastapi
uvicorn
```