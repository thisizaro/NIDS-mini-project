# CICFlowMeter API (Dockerized)

## Overview

This project provides a **REST API wrapper** around [**CICFlowMeter**](https://github.com/CanadianInstituteForCybersecurity/CICFlowMeter) using **FastAPI** and **Docker**.

The API accepts a **PCAP file**, processes it using CICFlowMeter inside a Docker container, and returns the generated **CSV flow files as a ZIP archive**.

This setup is designed to:

* Be easy to run
* Be reproducible using Docker
* Work with large PCAP files
* Keep the Java/Gradle logic isolated from the API layer

---

## How It Works (High Level)

1. Client uploads a PCAP file via API
2. PCAP is saved to `/pcap` inside the container
3. CICFlowMeter is executed using Gradle
4. CSV flow files are generated in `/flow`
5. All CSVs are zipped
6. ZIP file is returned to the client

Only **one request is processed at a time**.

---

## Project Structure

```
/
├── api/            # FastAPI application
├── code/           # CICFlowMeter source (cloned in Docker)
├── pcap/           # Uploaded PCAP files
├── flow/           # Generated CSV flow files
├── gradle-task     # Custom Gradle task (runcmd)
├── Dockerfile
└── README.md
```

---

## Requirements

* Docker (Docker Desktop recommended)
* No local Java, Gradle, or Python setup required

---

## Build the Docker Image

From the project root:

```bash
docker build -t cicflow-api .
```

---

## Run the API

```bash
docker run -it --rm -p 8000:8000 --name cicflow-api-container cicflow-api
```

Once running, the API will be available at:

```
http://localhost:8000
```

---

## API Documentation (Swagger UI)

FastAPI automatically provides interactive documentation:

```
http://localhost:8000/docs
```

Use this page to:

* Upload a PCAP file
* Test the API directly from the browser

---

## API Endpoint

### `POST /process`

**Description:**
Uploads a PCAP file, processes it, and returns flow CSV files as a ZIP.

**Request:**

* `multipart/form-data`
* Single file upload (`.pcap`)

**Response:**

* `application/zip`
* Contains CSV flow files

---

## Notes & Assumptions

* Only one API request is processed at a time
* Temporary cleanup is minimal (PCAP files are removed after processing)
* This project currently runs entirely inside a Docker container
* Designed for experimentation and research use

---

## Author

**Aranya Dutta**

[thisizaro](https://github.com/thisizaro)

---

## License

This project is provided under the **MIT License**.

You are free to:

* Use
* Modify
* Distribute

With attribution.

CICFlowMeter itself is licensed separately --- please refer to its original repository for details.

---

## Acknowledgements

* Canadian Institute for Cybersecurity --- CICFlowMeter
* FastAPI
* Docker
