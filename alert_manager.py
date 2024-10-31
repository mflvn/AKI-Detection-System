import urllib
import urllib.error
import urllib.request
import os
from config import PAGER_PORT, PAGER_ADDRESS
import socket
import time

NUM_PAGING_RETRIES = 10 

class AlertManager:
    """
    AlertManager handles the communication with the hospital's alerting system.
    """

    @staticmethod
    def send_alert(patient_mrn: str, timestamp: str):
        """
        Send an alert for the specified patient MRN.

        Parameters:
        patient_mrn (str): The medical record number of the patient.
        timestamp (str): The timestamp of the alert in the format YYYYMMDDHHMMSS
        """
        socket.setdefaulttimeout(1)
        paged = False
        counter = 0
        while not paged and counter < NUM_PAGING_RETRIES:
            counter += 1
            try:
                alert_data = bytes(patient_mrn +','+timestamp, 'utf-8')
                r = urllib.request.urlopen(f"http://{PAGER_ADDRESS}:{PAGER_PORT}/page", data=alert_data)
                if 200 <= r.status  <= 300:
                    paged = True
                else:
                    time.sleep(1)
            except urllib.error.URLError as e:
                if counter == NUM_PAGING_RETRIES:
                    raise RuntimeError("Failed to page")
