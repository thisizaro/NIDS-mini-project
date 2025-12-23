# Deep Learning Based Intrusion Detection System

A machine learning-based Network Intrusion Detection System (NIDS) that uses a 2D CNN with OpenMax open-set recognition to detect and classify network attacks from PCAP traffic captures.

## Architecture

```
Frontend (React, :5173)
    |
    v
Orchestrator (FastAPI, :8080)
    |
    +---> CICFlowMeter (Docker, :8010)  -- PCAP to CSV flow features
    +---> Preprocessor (FastAPI, :8001)  -- Feature scaling & cleaning
    +---> Model Service (FastAPI, :8003) -- 2D CNN + OpenMax inference
    +---> Decision Engine (FastAPI, :8002) -- Severity & alert generation
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (for CICFlowMeter)

### 1. Install Dependencies

```bash
# Python dependencies (from project root)
pip install fastapi uvicorn httpx pandas numpy scipy scikit-learn joblib tensorflow python-multipart pydantic-settings python-json-logger

# Frontend
cd frontend && npm install && cd ..
```

### 2. Build CICFlowMeter Docker Image

```bash
cd cicflowmeter-docker-api
docker build -t cicflowmeter-api .
cd ..
```

### 3. Start All Services

```bash
bash start_all.sh
```

### 4. Open the Application

- **Dashboard**: http://localhost:5173/
- **Analyze PCAP**: http://localhost:5173/analyze
- **Service Testing**: http://localhost:5173/test

### Stop All Services

```bash
bash stop_all.sh
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| CICFlowMeter | 8010 | Converts PCAP files to CSV flow features (Docker) |
| Preprocessor | 8001 | Cleans, selects, and scales features |
| Model Service | 8003 | 2D CNN + OpenMax classification |
| Decision Engine | 8002 | Severity assessment & alert generation |
| Orchestrator | 8080 | API gateway coordinating all services |
| Frontend | 5173 | React dashboard with testing pages |

## Model

- **Architecture**: 2D CNN (Conv2D layers) with OpenMax open-set recognition
- **Training Data**: CICIDS2017 dataset
- **Classes**: Normal, DoS, Brute Force, PortScan, Botnet, Web Attack, Unknown
- **Accuracy**: 93.82% overall, Macro AUC: 0.8471
- **Features**: 67 network flow features reshaped to 11x11 images

## Project Structure

```
ml-ids-project/
├── frontend/                  # React + Vite + Tailwind frontend
├── orchestrator/              # API gateway service
├── preprocessor_module/       # Feature preprocessing service
├── model_service/             # 2D CNN inference service
├── decision_engine/           # Severity & alert service
├── cicflowmeter-docker-api/   # PCAP processing (Docker)
├── trained_models/            # Model weights, scalers, configs
│   ├── cnn_openmax/           # 2D CNN + OpenMax model
│   ├── preprocessing/         # Model scaler & feature config
│   ├── preprocessor/          # Preprocessor scaler
│   ├── autoencoder_results/   # Autoencoder experiment results
│   ├── vae/                   # VAE experiment results
│   ├── aae/                   # AAE experiment results
│   └── lstm_ae/               # LSTM AE experiment results
├── training_scripts/          # Model training notebooks & scripts
│   ├── notebooks/             # Training notebooks
│   ├── kaggle/                # Kaggle training scripts
│   ├── data_loader.py
│   ├── models.py
│   ├── trainer.py
│   └── evaluator.py
├── report_charts/             # Generated charts for report
├── start_all.sh               # Start all services
└── stop_all.sh                # Stop all services
```

## Training Scripts

The `training_scripts/` directory contains all model training code:

- `notebooks/cnn_openmax_training.ipynb` - 2D CNN + OpenMax (final model)
- `notebooks/vae_training.ipynb` - Variational Autoencoder
- `notebooks/cnnae_training.ipynb` - CNN Autoencoder
- `notebooks/infogan_training_optimized.ipynb` - InfoGAN
- `kaggle/cnn_openmax_final.ipynb` - Kaggle training notebook
- `kaggle/openmax_kaggle_v2.py` - OpenMax algorithm implementation

## Dataset

This project uses the [CICIDS2017](https://www.unb.ca/cic/datasets/ids-2017.html) dataset from the Canadian Institute for Cybersecurity. The dataset is not included in this repository due to size constraints. Download it separately for training.

## Technologies

- **Backend**: Python, FastAPI, TensorFlow/Keras, scikit-learn
- **Frontend**: React 19, Vite, Tailwind CSS
- **ML**: 2D CNN, OpenMax, Autoencoders, VAE, LSTM, InfoGAN
- **Infrastructure**: Docker, CICFlowMeter (Java)
