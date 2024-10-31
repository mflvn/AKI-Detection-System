import unittest
from message_parser import parse_message
from hospital_message import PatientAdmissionMessage, PatientDischargeMessage, TestResultMessage

class MessageParserTest(unittest.TestCase):
    
        
    def test_parsing_admission_message(self):
        """
        Test parsing of an admission message.
        """
        
        message_str = [
            'MSH|^~\&|SIMULATION|SOUTH RIVERSIDE|||20240102135300||ADT^A01|||2.5',
            'PID|1||497030||ROSCOE DOHERTY||19870515|M'
        ]
        
        parsed_object = parse_message(message_str)
        
        # Check if parsed object is of the correct type
        self.assertEqual(parsed_object.__class__.__name__, "PatientAdmissionMessage")
        
         # Create a PatientAdmissionMessage object for comparison
        expected_object = PatientAdmissionMessage('497030', 'ROSCOE DOHERTY', '1987-05-15', 'M')

        # Compare the attributes of the parsed object and the expected object
        self.assertEqual(parsed_object.mrn, expected_object.mrn)
        self.assertEqual(parsed_object.name, expected_object.name)
        self.assertEqual(parsed_object.date_of_birth, expected_object.date_of_birth)
        self.assertEqual(parsed_object.sex, expected_object.sex)
        
    def test_parsing_discharge_message(self):
        """
        Test parsing of a discharge message.
        """
        
        message_str = [
            'MSH|^~\&|SIMULATION|SOUTH RIVERSIDE|||20240804082900||ADT^A03|||2.5',
            'PID|1||583036'
        ]
        
        parsed_object = parse_message(message_str)
        
        # Check if parsed object is of the correct type
        self.assertEqual(parsed_object.__class__.__name__, "PatientDischargeMessage")
        
        # Create a PatientDischargeMessage object for comparison
        expected_object = PatientDischargeMessage('583036')
        
        # Compare the attributes of the parsed object and the expected object
        self.assertEqual(parsed_object.mrn, expected_object.mrn)
    
    
    def test_parsing_test_result_message_simple_creatine_result(self):
        """
        Test parsing of a test result message.
        """
        
        message_str = [
            'MSH|^~\&|SIMULATION|SOUTH RIVERSIDE|||20240804082600||ORU^R01|||2.5',
            'PID|1||853291',
            'OBR|1||||||20240804082600',
            'OBX|1|SN|CREATININE||80.3'
        ]
        
        parsed_object = parse_message(message_str)
        
        # Check if parsed object is of the correct type
        self.assertEqual(parsed_object.__class__.__name__, "TestResultMessage")
        
        # Create a TestResultMessage object for comparison
        expected_object = TestResultMessage('853291', '2024-08-04', '08:26:00', 80.3)
        
        # Compare the attributes of the parsed object and the expected object
        self.assertEqual(parsed_object.mrn, expected_object.mrn)
        self.assertEqual(parsed_object.test_date, expected_object.test_date)
        self.assertEqual(parsed_object.test_time, expected_object.test_time)
        self.assertEqual(parsed_object.creatinine_value, expected_object.creatinine_value)
        
        
    def test_parsing_test_result_message(self):
        """
        Test parsing of a test result message.
        """
        
        message_str = [
            'MSH|^~\&|SIMULATION|SOUTH RIVERSIDE|||20240804082600||ORU^R01|||2.5',
            'PID|1||853291',
            'OBR|1||||||20240804082600',
            'OBX|1|SN|CREATININE||80.36829888959176'
        ]
        
        parsed_object = parse_message(message_str)
        
        # Check if parsed object is of the correct type
        self.assertEqual(parsed_object.__class__.__name__, "TestResultMessage")
        
        # Create a TestResultMessage object for comparison
        expected_object = TestResultMessage('853291', '2024-08-04', '08:26:00', 80.36829888959176)
        
        # Compare the attributes of the parsed object and the expected object
        self.assertEqual(parsed_object.mrn, expected_object.mrn)
        self.assertEqual(parsed_object.test_date, expected_object.test_date)
        self.assertEqual(parsed_object.test_time, expected_object.test_time)
        self.assertEqual(parsed_object.creatinine_value, expected_object.creatinine_value)


if __name__ == '__main__':
    unittest.main()
