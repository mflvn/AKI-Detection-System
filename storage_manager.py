import csv
import datetime
import pandas as pd
import os
import argparse
import joblib
import numpy as np
from config import MESSAGE_LOG_CSV_PATH, MESSAGE_LOG_CSV_FIELDS, MODEL_PATH
from hospital_message import PatientAdmissionMessage, TestResultMessage, PatientDischargeMessage
import copy

from prometheus_client import Counter

p_sum_of_all_messages = Counter("sum_of_all_messages", "Number of all messages received AND reinstated")
p_sum_of_positive_aki_predictions = Counter("sum_of_positive_aki_predictions", "Number of all aki predictions from received AND reinstated")


p_reinstantiated_overall = Counter("reinstantiated_overall", "Number of overall messages reinstantiated from log")
p_reinstantiated_admission = Counter("reinstantiated_admission", "Number of admission messages reinstantiated")
p_reinstantiated_discharge = Counter("reinstantiated_discharge", "Number of discarded admission reinstantiated")
p_reinstantiated_test_result = Counter("reinstantiated_test_result", "Number of test result messages reinstantiated")
p_reinstantiation_errors = Counter("reinstantiation_errors", "Number of errors during message instantiation")

class StorageManager:
    """
    Manages storage and retrieval of patient data both in-memory and in a database.
    """
    def __init__(self,
                 fields: list = MESSAGE_LOG_CSV_FIELDS, 
                 message_log_filepath: str = MESSAGE_LOG_CSV_PATH,
                 model_path: str = MODEL_PATH):
        """
        Initializes the storage manager by setting up the database connection and sessionmaker.
        """
        # Stores creatinine results for all patients
        # The file history.csv is imported and the data is stored in this dictionary
        # The key is the MRN and the value is a list of creatinine results as floats
        # We only write to the creatinine_results_history when a patient is discharged
        self.creatinine_results_history = dict()
        
        
        # Stores data for patients currently admitted in the hospital
        # The key is the MRN and the value is a dictionary containing patient information
        # Entries are added when a patient is admitted and removed when a patient is discharged
        self.current_patients = dict()
        
        self.message_log_filepath = message_log_filepath
        self.fields = fields
        
        self.model = self.load_model(model_path)
    
    def initialise_database(self, history_csv_path, wipe_past_message_log: bool = False):
        # Read the history.csv file to populate the creatinine_results_history dictionary
        with open(history_csv_path, 'r') as file:
            reader = csv.reader(file)
            next(reader, None)  # Skip the header row
            for row in reader: 
                mrn = row[0]
                creatinine_results = [row[col] for col in range(2, len(row), 2) if row[col] != ""]
                creatinine_results = list(map(float, creatinine_results))
                self.creatinine_results_history[mrn] = creatinine_results
        
        # # Check if the CSV file does not exist, we create it
        if not os.path.exists(self.message_log_filepath):
            with open(self.message_log_filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fields)
                writer.writeheader()  # Write the header row
        else:
            if wipe_past_message_log:
                with open(self.message_log_filepath, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fields)
                    writer.writeheader()  # Write the header row
            else:
                self.instantiate_all_past_messages_from_log()
        
    def add_admitted_patient_to_current_patients(self, admission_msg: PatientAdmissionMessage):
        """
        Adds an admitted patient's data to the current_patients dictionary.
        """
        if admission_msg.mrn in self.creatinine_results_history:
            self.current_patients[admission_msg.mrn] = {
                'name': admission_msg.name,
                'date_of_birth': admission_msg.date_of_birth,
                'sex': admission_msg.sex,
                'creatinine_results': self.creatinine_results_history[admission_msg.mrn],
                'previous_positive_aki_prediction': False
                }
                
        else:
            self.current_patients[admission_msg.mrn] = {
                'name': admission_msg.name,
                'date_of_birth': admission_msg.date_of_birth,
                'sex': admission_msg.sex,
                'creatinine_results': [],
                'previous_positive_aki_prediction': False
                }
    
    def add_test_result_to_current_patients(self, test_results_msg: TestResultMessage):
        """
        Appends a new test result for a patient in the in-memory dictionary.
        """
        if test_results_msg.mrn in self.current_patients:
            self.current_patients[test_results_msg.mrn]['creatinine_results'].append(float(test_results_msg.creatinine_value))
        else:
            raise ValueError(f"The lab results of patient {test_results_msg.mrn} cannot be processed," +
                             "since there is no record of an HL7 admission message for this patient.")
            
    def remove_patient_from_current_patients(self, discharge_msg: PatientDischargeMessage):
        """
        Removes a patient's information from the in-memory storage.
        """
        if discharge_msg.mrn in self.current_patients:
            self.current_patients.pop(discharge_msg.mrn, None)
        else:
            raise ValueError(f"The discharge of patient {discharge_msg.mrn} cannot be processed," + 
                             "since there is no record of an HL7 admission message for this patient.")
        
    def update_patients_data_in_creatinine_results_history(self, discharge_msg: PatientDischargeMessage):
        """
        Updates the creatinine results history for a discharged patient.
        """
        self.creatinine_results_history[discharge_msg.mrn] = self.current_patients[discharge_msg.mrn]['creatinine_results']
    
    def no_positive_aki_prediction_so_far(self, mrn):
        """
        Checks if previously a positive aki prediction was triggered
        """
        return not self.current_patients[mrn]['previous_positive_aki_prediction']
    
    def update_positive_aki_prediction_to_current_patients(self, mrn):
        """
        Records to memory that a positive aki prediction was triggered
        """
        self.current_patients[mrn]['previous_positive_aki_prediction'] = True
    
    def add_message_to_log_csv(self, message: object):
        """
        Appends a message as a single row to message_log.csv.
        """
        # Prepare the message data based on the type of message
        if isinstance(message, PatientAdmissionMessage):
            row_data = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'PatientAdmission',
                'mrn': message.mrn,
                'additional_info': f"Name: {message.name}. DOB: {message.date_of_birth}. Sex: {message.sex}"
            }
        elif isinstance(message, PatientDischargeMessage):
            row_data = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'PatientDischarge',
                'mrn': message.mrn,
                'additional_info': ''
            }
        elif isinstance(message, TestResultMessage):
            row_data = {
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'TestResult',
                'mrn': message.mrn,
                'additional_info': f"Test Date: {message.test_date}. Test Time: {message.test_time}. Creatinine Value: {message.creatinine_value}"
            }
        
        # Append single row to the CSV file
        with open(self.message_log_filepath, 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames= self.fields)
            writer.writerow(row_data)

    def instantiate_all_past_messages_from_log(self):
        """
        Reads message_log.csv, sorts messages chronologically, and creates message object instances.
        """
        df = pd.read_csv(self.message_log_filepath)         
        for _, row in df.iterrows():
            p_sum_of_all_messages.inc()
            p_reinstantiated_overall.inc()
            if row[1] == 'PatientAdmission':
                # Assuming additional_info contains comma-separated data
                info_parts = row[3].split('. ')
                mrn = str(row[2])
                name = info_parts[0].split(': ')[1]
                dob = info_parts[1].split(': ')[1]
                sex = info_parts[2].split(': ')[1]
                self.add_admitted_patient_to_current_patients(
                    PatientAdmissionMessage(mrn, name, dob, sex))
                p_reinstantiated_admission.inc()
            elif row[1] == 'PatientDischarge':
                mrn = str(row[2])
                try:
                    self.remove_patient_from_current_patients(
                        PatientDischargeMessage(mrn))
                    p_reinstantiated_discharge.inc()
                except ValueError: 
                    p_reinstantiation_errors.inc()
                
            elif row[1] == 'TestResult':
                info_parts = row[3].split('. ')
                mrn = str(row[2])
                test_date = info_parts[0].split(': ')[1]
                test_time = info_parts[1].split(': ')[1]
                creatinine_value = info_parts[2].split(': ')[1]
                try:
                    self.add_test_result_to_current_patients(
                    TestResultMessage(mrn, 
                                        test_date,
                                        test_time, 
                                        creatinine_value))
                    p_reinstantiated_test_result.inc()
                except ValueError: 
                    p_reinstantiation_errors.inc()
                    continue
                if self.no_positive_aki_prediction_so_far(mrn):
                    prediction_result = self.predict_aki(mrn)
                    if prediction_result == 1:
                        self.update_positive_aki_prediction_to_current_patients(mrn)
                        p_sum_of_positive_aki_predictions.inc()
            else:
                p_reinstantiation_errors.inc()
                
                
    def load_model(self, model_path: str):
        """Loads the predictive model from a file.

        Returns:
        The loaded predictive model.
        """

        model = joblib.load(model_path)
        return model

    @staticmethod
    def determine_age(date_of_birth: str) -> int:
        """
        Determine the age of the patient.

        Parameters:
        date_of_birth (str): The date of birth of the patient in the format YYYY-MM-DD.

        Returns:
        int: The age of the patient.
        """
        today = datetime.date.today()
        dob = datetime.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
        return int(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
    
    def predict_aki(self, mrn: str, num_creatinine_results = 5) -> int:
        """
        Predicts whether a patient is at risk of AKI based on their medical record number (MRN).

        Parameters:
        mrn (str): The medical record number of the patient.

        Returns:
        int: 0 if no AKI is predicted, 1 if AKI is predicted.
        """
        # Access the data from current_patients dictionary
        patient_data = self.current_patients.get(mrn)

        if patient_data is None:
            raise ValueError(f"Patient with MRN {mrn} not found in current_patients dictionary.")

        sex = 0 if patient_data['sex'].lower() == 'm' else 1
        age = self.determine_age(patient_data['date_of_birth'])

        creatinine_results = patient_data['creatinine_results'].copy()

        # Adjust creatinine results to match model input requirements
        if len(creatinine_results) > num_creatinine_results:
            recent_results = creatinine_results[-num_creatinine_results:]
        else:
            while len(creatinine_results) < num_creatinine_results:
                creatinine_results.append(creatinine_results[-1])
            recent_results = creatinine_results
        
        input_features = [age, sex] + recent_results
        return self.model.predict(np.array(input_features, dtype=np.float64).reshape(1, -1))[0]


if __name__ == "__main__":
    storage_manager = StorageManager()
    storage_manager.initialise_database()
    