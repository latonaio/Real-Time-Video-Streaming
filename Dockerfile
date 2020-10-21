FROM l4t-ds-opencv-7.2:latest

# Definition of a Device & Service
ENV POSITION=Runtime \
    SERVICE=real-time-video-streaming \
    AION_HOME=/var/lib/aion

# Setup Directoties
RUN mkdir -p ${AION_HOME}/$POSITION/$SERVICE
WORKDIR ${AION_HOME}/$POSITION/$SERVICE/

# Install dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libcairo2-dev \
    gcc \
    python3-dev \
    libgirepository1.0-dev \
    uvccapture \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-doc \
    gstreamer1.0-tools \
    python-gst-1.0 \
    python3-gst-1.0 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

ADD main.py .

CMD ["python3","-u", "main.py"]