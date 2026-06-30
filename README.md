\# Alerta Pública 🔍



AI-powered transparency monitor for Peruvian public procurement.



\## Overview



Alerta Pública analyzes real contracting data from Peru's SEACE system 

to automatically detect anomalies and suspicious patterns using machine 

learning and heuristic algorithms.



\## Key Features



\- \*\*Isolation Forest\*\* anomaly detection on contract amounts

\- \*\*Heuristic rules\*\*: dominant suppliers, abnormally fast processes, 

&#x20; price deviations

\- \*\*Composite risk scoring\*\* (0-100) per contract

\- \*\*AI-generated explanations\*\* via LLaMA 3.3 70B (Groq)

\- \*\*Interactive dashboard\*\* with filters by region and risk level



\## Data Source



Public procurement data from 

\[SEACE - OECE Peru](https://contratacionesabiertas.osce.gob.pe/)  

\- 21,946 contracts analyzed  

\- S/ 16.8 billion monitored  

\- 1,099 anomalies detected (5% of total)



\## Tech Stack



\- \*\*Backend\*\*: Python, FastAPI, scikit-learn, pandas, SQLite

\- \*\*ML\*\*: Isolation Forest, StandardScaler

\- \*\*AI\*\*: LLaMA 3.3 70B via Groq API

\- \*\*Frontend\*\*: HTML, CSS, JavaScript, Chart.js



\## Setup



```bash

cd backend

python -m venv venv

venv\\Scripts\\activate

pip install -r requirements.txt

\# Add your GROQ\_API\_KEY to backend/.env

python ingest.py

python detector.py

uvicorn main:app --reload

```



Open `frontend/index.html` in your browser.



\## Results



| Metric | Value |

|--------|-------|

| Contracts analyzed | 21,946 |

| Total monitored | S/ 16.8B |

| Anomalies detected | 1,099 |

| Suspicious rate | 5.0% |

| Max risk score | 70/100 |



\## Author



Gerald Stevens Rojas — Computer Science applicant, COAR Lima IB Graduate

