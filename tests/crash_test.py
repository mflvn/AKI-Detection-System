import unittest
from storage_manager import StorageManager
from hospital_message import PatientAdmissionMessage, TestResultMessage, PatientDischargeMessage

class TestRecoveryProcess(unittest.TestCase):
    def setUp(self):
        """Set up the test environment and simulate initial message processing."""
        message_log_filepath = 'message_log_crash_test.csv'
        self.storage_manager = StorageManager(message_log_filepath=message_log_filepath)
        self.storage_manager.initialise_database('history.csv', wipe_past_message_log = True,)

        
        # Simulate processing of HL7 messages
        admission_messages = (PatientAdmissionMessage('123', 'John Doe', '1990-01-01', 'M'),
                              PatientAdmissionMessage('124', 'Jane Doe', '1991-01-01', 'F'),
                              # For the next patients, the MRN results past creatinine 
                              # results exist in the history.csv file
                              PatientAdmissionMessage('822825', 'John Smith', '1992-01-01', 'M'),
                              PatientAdmissionMessage('172293', 'Jane Smith', '1993-01-01', 'F'))
        
        for admission_message in admission_messages:
            self.storage_manager.add_admitted_patient_to_current_patients(admission_message)
            self.storage_manager.add_message_to_log_csv(admission_message)
        
        test_result_messages = (TestResultMessage('124', '2021-01-01', '08:00', 1.2),
                                TestResultMessage('822825', '2021-01-01', '08:00', 101.2),
                                TestResultMessage('172293', '2021-01-01', '08:00', 56.4),
                                TestResultMessage('172293', '2021-01-01', '08:00', 74.2))
        
        for test_result_message in test_result_messages:
            self.storage_manager.add_test_result_to_current_patients(test_result_message)
            self.storage_manager.add_message_to_log_csv(test_result_message)
        
        discharge_messages = [PatientDischargeMessage('123')]
        
        for discharge_message in discharge_messages:
            self.storage_manager.update_patients_data_in_creatinine_results_history(discharge_message)
            self.storage_manager.remove_patient_from_current_patients(discharge_message)
            self.storage_manager.add_message_to_log_csv(discharge_message)
        
    def simulate_crash(self):
        """Simulate a crash by clearing the dictionaries."""
        self.storage_manager.current_patients.clear()
        self.storage_manager.creatinine_results_history.clear()

    def test_recovery_process(self):
        """Test the recovery process from message_log.csv."""
        # Simulate a crash
        self.simulate_crash()

        # Verify that the data structures are empty
        self.assertEqual(len(self.storage_manager.current_patients), 0)
        self.assertEqual(len(self.storage_manager.creatinine_results_history), 0)

        # Simulate the recovery process
        # This would read from message_log.csv and repopulate the dictionaries
        self.storage_manager.initialise_database('history.csv')
    
        self.assertIn('124', self.storage_manager.current_patients)
        self.assertIn('822825', self.storage_manager.current_patients)
        self.assertIn('172293', self.storage_manager.current_patients)

        self.assertEqual(self.storage_manager.current_patients['124']['creatinine_results'], [1.2])
        self.assertEqual(self.storage_manager.current_patients['172293']['creatinine_results'], [111.98,91.21,105.09,93.44,110.52,56.4,74.2])
        self.assertEqual(self.storage_manager.current_patients['822825']['creatinine_results'], [68.58,70.58,64.15,48.39,58.01,85.93,101.2])

if __name__ == '__main__':
    unittest.main()
