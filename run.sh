set +u
CONFIG_PATH=/data/options.json

USERNAME=$(jq --raw-output ".mqtt_username" $CONFIG_PATH)
PASSWORD=$(jq --raw-output ".mqtt_password" $CONFIG_PATH)
HOST=$(jq --raw-output ".mqtt_host" $CONFIG_PATH)
PORT=$(jq --raw-output ".mqtt_port" $CONFIG_PATH)

echo Starting radioGPIO2MQTT
python3 radioGPIO2MQTT.py $HOST $PORT $USERNAME $PASSWORD
echo radioGPIO2MQTT has stopped

