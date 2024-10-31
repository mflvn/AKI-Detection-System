import socket
import time
import threading
import sys
import signal
import os
import pandas as pd
import datetime
import time
import argparse

from prometheus_client import Gauge, Counter, Histogram, start_http_server

from config import MLLP_PORT, MLLP_ADDRESS, PROMETHEUS_PORT, MESSAGE_LOG_CSV_PATH, HISTORY_CSV_PATH

from storage_manager import StorageManager
from message_parser import parse_message
from hospital_message import PatientAdmissionMessage, TestResultMessage, PatientDischargeMessage
from alert_manager import AlertManager

from storage_manager import p_sum_of_all_messages, p_sum_of_positive_aki_predictions

MLLP_START_OF_BLOCK = 0x0b
MLLP_END_OF_BLOCK = 0x1c
MLLP_CARRIAGE_RETURN = 0x0d

#General message metrics
p_overall_messages_received = Gauge("overall_messages_received", "Number of overall messages received")
p_overall_messages_acknowledged = Counter("overall_messages_acknowledged", "Number of overall messages received")

#Message type and handlings metrics
p_admission_messages = Counter("admission_messages_received", "Number of valid admission messages received")
p_successful_admission_message_handlings = Counter("successful_admission_message_handlings", "Number of valid admission messages received and handled correctly")

p_discharge_messages = Counter("discharge_messages_received", "Number of discharge messages received")
p_successful_discharge_message_handlings = Counter("successful_discharge_message_handlings", "Number of valid discharge messages received and handled correctly")

p_test_result_messages = Counter("test_result_messages_received", "Number of test result messages received")
p_successful_test_result_handlings = Counter("test_result_successful_handled", "Number of cases where the test result was not added to the storage manager due to not having the patient in the current patients list")

#Predictions and pagings
p_positive_aki_predictions = Counter("positive_aki_predictions", "Number of positive aki predictions")
p_negative_aki_predictions = Counter("negative_aki_predictions", "Number of negative aki predictions")
p_number_of_pagings = Counter("number_of_pagings", "Number of times hospital staff has been paged")
p_failed_pagings = Counter("failed_pagings", "Number of times paging failed")

#Log metrics
p_messages_added_to_log = Counter("messages_added_to_log", "Number of messages added to the log")

#Latency metrics
p_paging_latency = Histogram('paging_latency', 'Time to page positive aki_prediction', buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 3, 4, 5, 10, 20, 40, 60, 120, 600, 1200])
p_message_latency = Histogram('message_latency', 'Time to process message', buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 3, 4, 5, 10, 20, 40, 60, 120, 600, 1200])

#Connection and reconnection metrics
p_connection_closed_error = Counter("connection_closed_error", "Number of times socket connection closed")
p_number_of_connection_attempts = Counter("number_of_connection_attempts", "Number of times socket connection was attempted")

#Badly handled messages
p_message_errors = Counter("message_errors", "Number of times a message was badly handled")

start_http_server(PROMETHEUS_PORT)

global stopping_condition
stopping_condition = False

def shutdown():
    global stopping_condition
    stopping_condition = True
    print("graceful shutdown")
    sys.exit(0)
    
signal.signal(signal.SIGTERM, shutdown)

def parse_mllp_messages(buffer, source):
    i = 0
    messages = []
    consumed = 0
    expect = MLLP_START_OF_BLOCK
    while i < len(buffer):
        if expect is not None:
            if buffer[i] != expect:
                raise Exception(f"{source}: bad MLLP encoding: want {hex(expect)}, found {hex(buffer[i])}")
            if expect == MLLP_START_OF_BLOCK:
                expect = None
                consumed = i
            elif expect == MLLP_CARRIAGE_RETURN:
                messages.append(buffer[consumed+1:i-1])
                expect = MLLP_START_OF_BLOCK
                consumed = i + 1
        else:
            if buffer[i] == MLLP_END_OF_BLOCK:
                expect = MLLP_CARRIAGE_RETURN
        i += 1
    return messages, buffer[consumed:]

def initialise_system(message_log_filepath : str = MESSAGE_LOG_CSV_PATH):
    """
    Initialises the environment for the aki prediction system.
    
    This function creates the necessary objects for the system to work, namely the storage manager and the alert manager, 
    It also loads past data to make the system up to date.
    
    Args:
        message_log_filepath (str): The path to the message log file.
        
    Returns:
        storage_manager (StorageManager): The storage manager object.
        alert_manager (AlertManager): The alert manager object.
    """
    storage_manager = StorageManager(message_log_filepath = message_log_filepath)
    alert_manager = AlertManager()
    storage_manager.initialise_database(history_csv_path=HISTORY_CSV_PATH)
    
    return storage_manager, alert_manager

def to_mllp(segments: list):
    MLLP_START_OF_BLOCK = 0x0b
    MLLP_END_OF_BLOCK = 0x1c
    MLLP_CARRIAGE_RETURN = 0x0d
    m = bytes(chr(MLLP_START_OF_BLOCK), "ascii")
    m += bytes("\r".join(segments) + "\r", "ascii")
    m += bytes(chr(MLLP_END_OF_BLOCK) + chr(MLLP_CARRIAGE_RETURN), "ascii")
    return m

def from_mllp(buffer):
    return str(buffer[:-1], "ascii").split("\r") # Strip MLLP framing and final \r

def send_ack(s: socket.socket):
    ack_raw = [f"MSH|^~\&|||||{datetime.datetime.now().strftime('%Y%M%D%H%M%S')}||ACK|||2.5",
                    "MSA|AA",]
    ack = to_mllp(ack_raw)
    s.sendall(ack)

def listen_for_messages(storage_manager: StorageManager, 
                        alert_manager: AlertManager,
                        address: tuple[str, int] = (MLLP_ADDRESS, MLLP_PORT), 
                        retries: int = 20,
                        start_delay: float = 1.0,
                        max_delay: float = 30.0) -> None:
    """Receives HL7 messages over a socket, decodes, and queues them for
    processing.
   
    Args:
        address (tuple[str, int]): Hostname and port number for the socket
                                   connection.
        retries (int): number of reconnection attempts.
        start_delay (float): Initial delay between reconnection attempts
                            in seconds. Delays increase exponentially.
        max_delay (float): Maximum delay between reconnection attempts
                           in seconds.
    """
    global stopping_condition
    source = f"{MLLP_ADDRESS}:{MLLP_PORT}"
    buffer = b""
    attempt_count = 0
    delay = start_delay
    while not stopping_condition and attempt_count < retries:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                print("Attempting to connect...")
                p_number_of_connection_attempts.inc()
                s.connect(address)
                print("Connected!")
                attempt_count = 0
                delay = start_delay
                
                while not stopping_condition:
                    r = s.recv(1024)
                    if len(r) == 0:
                        continue
                    time_message_received = time.time()
                    p_sum_of_all_messages.inc()
                    p_overall_messages_received.inc()
                    buffer += r
                    received, buffer = parse_mllp_messages(buffer, source)
                    try:
                        message_object = parse_message(from_mllp(received[0]))
                        
                        if isinstance(message_object, PatientAdmissionMessage):
                            p_admission_messages.inc()
                            storage_manager.add_admitted_patient_to_current_patients(message_object)
                            p_successful_admission_message_handlings.inc()
                            
                        elif isinstance(message_object, TestResultMessage):
                            p_test_result_messages.inc()
                            storage_manager.add_test_result_to_current_patients(message_object)
                            p_successful_test_result_handlings.inc()

                            if storage_manager.no_positive_aki_prediction_so_far(message_object.mrn):
                                prediction_result = storage_manager.predict_aki(message_object.mrn)
                                if prediction_result == 1:
                                    p_positive_aki_predictions.inc()
                                    p_sum_of_positive_aki_predictions.inc()
                                    try:
                                        alert_manager.send_alert(message_object.mrn, message_object.timestamp) 
                                    except RuntimeError:
                                        p_failed_pagings.inc()
                                    p_number_of_pagings.inc()
                                    time_latency_aki_paging = time.time() - time_message_received
                                    p_paging_latency.observe(time_latency_aki_paging)
                                    
                                    storage_manager.update_positive_aki_prediction_to_current_patients(message_object.mrn)
                                elif prediction_result == 0:
                                    p_negative_aki_predictions.inc()
                                        
                        elif isinstance(message_object, PatientDischargeMessage):
                            p_discharge_messages.inc()
                            storage_manager.remove_patient_from_current_patients(message_object)
                            p_successful_discharge_message_handlings.inc()
                            
                        storage_manager.add_message_to_log_csv(message_object)
                        p_messages_added_to_log.inc()
                        
                    except ValueError:
                        p_message_errors.inc()
                        
                    finally: 
                        send_ack(s)
                        p_overall_messages_acknowledged.inc()
                        time_message_latency = time.time() - time_message_received
                        p_message_latency.observe(time_message_latency)
                      
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(delay)
            delay = min(delay * 2, max_delay)
            attempt_count += 1
            print(f"Attempting to reconnect, attempt {attempt_count}.")
 
        if attempt_count == retries:
            print("Maximum reconnection attempts reached, stopping.")
            stopping_condition = True
        print("Closing server socket.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AKI Prediction System')
    parser.add_argument('--history-dir', type=str, help='Path to history CSV file')
    args = parser.parse_args()

    if args.history_dir:
        HISTORY_CSV_PATH = args.history_dir
    else:
        pass

    storage_manager, alert_manager = initialise_system()
    listen_for_messages(storage_manager, alert_manager)
