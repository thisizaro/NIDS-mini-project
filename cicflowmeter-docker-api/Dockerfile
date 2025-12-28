FROM ubuntu:18.04

# ---- System dependencies ----
RUN apt-get update && \
    apt-get install -y \
        openjdk-8-jdk \
        gradle \
        maven \
        git \
        libpcap-dev \
        python3.8 \
        python3.8-distutils \
        curl && \
    rm -rf /var/lib/apt/lists/*


# ---- Install pip for Python 3.8 ----
RUN curl -sS https://bootstrap.pypa.io/pip/3.8/get-pip.py | python3.8

# ---- Required directories ----
RUN mkdir /pcap /flow /api

# ---- CICFlowMeter setup ----
RUN git clone https://github.com/CanadianInstituteForCybersecurity/CICFlowMeter /code

RUN cd /code/jnetpcap/linux/jnetpcap-1.4.r1425 && \
    mvn install:install-file \
        -Dfile=jnetpcap.jar \
        -DgroupId=org.jnetpcap \
        -DartifactId=jnetpcap \
        -Dversion=1.4.1 \
        -Dpackaging=jar

# ---- Inject custom Gradle task ----
WORKDIR /code


# ---- Build CICFlowMeter ----
RUN gradle --no-daemon build

COPY gradle-task /gradle-task
RUN cat /gradle-task >> build.gradle && rm /gradle-task

# ---- API setup ----
COPY api /api
WORKDIR /api
RUN python3.8 -m pip install --no-cache-dir -r requirements.txt

# ---- Networking ----
EXPOSE 8000

# ---- Run FastAPI ----
CMD ["python3.8", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
