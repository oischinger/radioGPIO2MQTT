ARG BUILD_FROM
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Install requirements for add-on
RUN apk add --no-cache clang
RUN apk add --no-cache libgcc
RUN apk add --no-cache gcc-gnat
RUN apk add --no-cache libgc++
RUN apk add --no-cache g++
RUN apk add --no-cache make
RUN apk add --no-cache python3-dev
RUN apk add --no-cache python3
RUN apk add --no-cache py3-pip
RUN pip3 install RPi.GPIO
RUN pip3 install paho-mqtt

# Copy data for add-on
COPY run.sh /
COPY radioGPIO2MQTT.py /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

