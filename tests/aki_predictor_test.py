import unittest
import numpy as np
from datetime import datetime, date
from storage_manager import StorageManager

class AKIPredictorTest(unittest.TestCase):
    def setUp(self):
        self.storage_manager = StorageManager()
        
    def test_predict_aki_positive_case(self):
        test_mrn = '12345'
        test_patient_data_jane = {
            'name': 'Jane Doe',
            'sex': 'f',
            'date_of_birth': '1990-01-01',
            'creatinine_results': [60.7, 62.3, 53, 80, 165, 204.56]
        }
        self.storage_manager.current_patients[test_mrn] = test_patient_data_jane
        
        result = self.storage_manager.predict_aki(test_mrn)

        self.assertEqual(result, 1)
    
    def test_predict_aki_negative_case(self):
        test_mrn = '654321'
        test_patient_data_jon = {
            'name': 'Jon Doe',
            'sex': 'm',
            'date_of_birth': '1950-01-01',
            'creatinine_results': [60.7, 60.7, 61.7]
        }
        self.storage_manager.current_patients[test_mrn] = test_patient_data_jon
        
        result = self.storage_manager.predict_aki(test_mrn)

        self.assertEqual(result, 0)   
    

if __name__ == '__main__':
    unittest.main()
