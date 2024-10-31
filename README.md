# SWEML AKI prediction Project

## Description

This project performs Acute Kidney Injury prediction based on creatinine test results 

## Installation

1. Clone the repository:
    - With SSH: `git clone git@gitlab.doc.ic.ac.uk:glg23/sweml.git`
    - With HTTPS: `git clone https://gitlab.doc.ic.ac.uk/glg23/sweml.git`


## Running locally

1. Install the dependencies: `pip install -r requirements.txt`
2. Edit the `HISTORY_CSV_PATH` variable in config.py to `'history.csv'`, and the `MESSAGE_LOG_CSV_PATH` to `'message_log.csv'`
3. Run message_listener.py using the following command in the terminal: `PAGER_ADDRESS=localhost:8441 MLLP_ADDRESS=localhost:8440 python message_listener.py`. Change ports and addresses according to your specific needs. 
4. Run simulator.py to simulate a stream of messages on port 8440 and a pager endpoint on port 8441

Note that with the current implementation, the system will attempt to reconnect with the simulator after the sequence of messages ends. This is necessary for the code to work on Kubernetes, but means that on Docker or locally, with a non-continuous stream of messages, the code might not stop. 

To run the tests using `unittest`, follow these steps:

To run a specific test use the following command: `python3 -m unittest tests.<test_name>`
Run all tests using the following command: `python -m unittest discover -s tests -p '*_test.py'`

The tests will be executed and the results will be displayed in the terminal or command prompt.

## Running on Docker

1. Edit the `HISTORY_CSV_PATH` variable in config.py to `'/data/history.csv'`, and the `MESSAGE_LOG_CSV_PATH` to `'message_log.csv'`
2. Run the following command to build the image: `docker build -t <image_name> .`
3. To run a container, run the following command: `docker run --env MLLP_ADDRESS=host.docker.internal:8440 --env PAGER_ADDRESS=host.docker.internal:8441 -v ${PWD}:/data <image_name>`. If necessary, change the environment variables.
4. Run simulator.py to simulate a stream of messages on port 8440 and a pager endpoint on port 8441

## Running on Kubernetes
1. Edit the `HISTORY_CSV_PATH` variable in config.py to `'/hospital-history/history.csv'`, and the `MESSAGE_LOG_CSV_PATH` to `'/state/message_log.csv'`
2. Login to azure using the command `az login`
3. To delete any existing pod (this will not delete our persistent state - state should NOT be deleted for simulator 5 and 6): `kubectl delete deploy aki-detection -n <team_name>`
You can check for current deployments using`kubectl --namespace=emilia get deployments`
4. Build the docker image:
`docker build --platform=linux/x86_64 -t imperialswemlsspring2024.azurecr.io/<image_name>-<team_name> . --no-cache`
5. Push the docker image: `docker push imperialswemlsspring2024.azurecr.io/<image_name>-<team_name>`
6. Edit the yaml config file to match the name of your image
7. Create the deployment
`kubectl apply -f <yaml_file_name>`
8. Monitor the prometheus metrics by forwarding the metrics from kubernetes to your local host
`kubectl port-forward -n <team_name> <pod_name> 8000:8000`
9. Then go to localhost:8000