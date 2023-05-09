FROM python:3.10-bullseye

RUN apt-get update && apt-get install -y sqlite3 libgeos-dev lz4 wget g++ cmake cmake-curses-gui make libexpat1-dev zlib1g-dev libbz2-dev libsparsehash-dev \
    libboost-program-options-dev libboost-dev libgdal-dev libproj-dev libsqlite3-mod-spatialite libspatialindex-dev

RUN mkdir -p /usr/src/app/

WORKDIR /usr/src/app/

COPY . ./

RUN pip install -r requirements.txt

