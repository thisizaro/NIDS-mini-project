#!/bin/bash

echo "==================================="
echo "Verdict Service - Example Requests"
echo "==================================="
echo ""

BASE_URL="http://localhost:8000/api/v1"

echo "1. Health Check"
echo "-----------------------------------"
curl -s $BASE_URL/health | python3 -m json.tool
echo -e "\n"

echo "2. Normal Traffic (LOW)"
echo "-----------------------------------"
curl -s -X POST $BASE_URL/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "normal",
      "attack_detected": false,
      "confidence": 0.98,
      "flow_count": 1178
    },
    "context": {
      "networkZone": "Internal",
      "assetCriticality": "High"
    }
  }' | python3 -m json.tool
echo -e "\n"

echo "3. Port Scan - External/Low (MEDIUM)"
echo "-----------------------------------"
curl -s -X POST $BASE_URL/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "abnormal",
      "attack_detected": true,
      "attack_type": "PortScan",
      "confidence": 0.78,
      "reconstruction_error": 0.70,
      "threshold": 0.65,
      "flow_count": 450
    },
    "context": {
      "networkZone": "External",
      "assetCriticality": "Low"
    }
  }' | python3 -m json.tool
echo -e "\n"

echo "4. DDoS - Internal/High (CRITICAL)"
echo "-----------------------------------"
curl -s -X POST $BASE_URL/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "abnormal",
      "attack_detected": true,
      "attack_type": "DDoS",
      "confidence": 0.91,
      "reconstruction_error": 0.87,
      "threshold": 0.65,
      "flow_count": 1178
    },
    "context": {
      "networkZone": "Internal",
      "assetCriticality": "High"
    }
  }' | python3 -m json.tool
echo -e "\n"

echo "5. Ransomware - DMZ/Medium (CRITICAL)"
echo "-----------------------------------"
curl -s -X POST $BASE_URL/verdict \
  -H "Content-Type: application/json" \
  -d '{
    "modelFindings": {
      "status": "abnormal",
      "attack_detected": true,
      "attack_type": "Ransomware",
      "confidence": 0.88,
      "reconstruction_error": 0.95,
      "threshold": 0.65,
      "flow_count": 823
    },
    "context": {
      "networkZone": "DMZ",
      "assetCriticality": "Medium"
    }
  }' | python3 -m json.tool
echo -e "\n"
