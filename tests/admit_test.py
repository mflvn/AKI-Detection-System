import unittest
from storage_manager import StorageManager
from hospital_message import PatientAdmissionMessage, TestResultMessage, PatientDischargeMessage

class TestPatientDataPersistence(unittest.TestCase):
    """
    A test case for verifying the persistence of patient data across admissions within a healthcare system.
    """
    
    def setUp(self):
        """
        Prepare resources and initial conditions for the tests.
        
        Initialises a new StorageManager instance with empty dictionaries for creatinine_results_history
        and current_patients to simulate a fresh start for each test method.
        """
        self.storage_manager = StorageManager()
    
    
    def test_patient_data_persistence_across_admissions(self):
        """
        Tests that a patient's lab test results are retained in the system even
        after discharge and are accessible upon re-admission.
        
        The test simulates the following sequence of events:
        1. A patient is admitted to the hospital.
        2. A lab test result is recorded for the patient.
        3. The patient is discharged from the hospital.
        4. The patient is readmitted to the hospital.
        
        The test verifies that the lab test results recorded during the first 
        admission are still associated with the patient after re-admission.
        """
        # Step 1: Admit the patient
        self.storage_manager.add_admitted_patient_to_current_patients(
            PatientAdmissionMessage('001', 'John Doe', '1980-01-01', 'M')
        )
        
        # Step 2: Record a test result
        self.storage_manager.add_test_result_to_current_patients(
            TestResultMessage('001', '2023-01-01', '08:00', 1.2)
        )
        
        # Verify test result is recorded
        self.assertIn(1.2, self.storage_manager.current_patients['001']['creatinine_results'])
        self.assertTrue(self.storage_manager.current_patients['001'] == {'name': 'John Doe', 'date_of_birth': '1980-01-01', 'sex': 'M', 'creatinine_results': [1.2], 'previous_positive_aki_prediction': False})

        # Step 3: Discharge the patient
        self.storage_manager.update_patients_data_in_creatinine_results_history(
            PatientDischargeMessage('001')
        )
        self.storage_manager.remove_patient_from_current_patients(PatientDischargeMessage('001'))
        
        # Step 4: Re-admit the patient
        self.storage_manager.add_admitted_patient_to_current_patients(
            PatientAdmissionMessage('001', 'John Doe', '1980-01-01', 'M')
        )

        # Verify the old lab test results are still accessible
        self.assertIn('001', self.storage_manager.creatinine_results_history)
        self.assertTrue(len(self.storage_manager.creatinine_results_history['001']) > 0)
        self.assertIn(1.2, self.storage_manager.creatinine_results_history['001'])

if __name__ == '__main__':
    unittest.main()
