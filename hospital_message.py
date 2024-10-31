class PatientAdmissionMessage():
    """
    Handles patient admission messages.
    """
    def __init__(self, mrn: str, name: str, date_of_birth: str, sex: str) -> None:
        """
        Initializes a patient admission message.

        Args:
            mrn (str): The medical record number of the patient.
            name (str): The name of the patient.
            date_of_birth (str): The date of birth of the patient, in the format
                                    '2021-01-01'.
            sex (str): The sex of the patient: 'M' or 'F'.

        Returns:
            None
        """
        self.mrn = mrn
        self.name = name
        self.date_of_birth = date_of_birth
        self.sex = sex
           
class PatientDischargeMessage():
    """
    Handles patient discharge messages.
    """
    def __init__(self, mrn: str) -> None:
        """
        Initializes a patient discharge message.

        Args:
            mrn (str): The medical record number of the patient.

        Returns:
            None
        """
        self.mrn = mrn
   
class TestResultMessage():
    """
    Handles test result messages.
    """
    def __init__(self, mrn: str, test_date: str, test_time: str, creatinine_value: float) -> None:
        """
        Initializes a patient admission message.

        Args:
            mrn (str): The medical record number of the patient.
            test_date (str): The date of the test, in the format '2021-01-01'.
            test_time (str): The time of the test, in the format '08:00'.
            creatinine_value (float): The value of the creatinine test.

        Returns:
            None
        """
        self.mrn = mrn
        self.test_date = test_date
        self.test_time = test_time
        self.creatinine_value = creatinine_value
        self.timestamp = test_date[0:4] + test_date[5:7] + test_date[8:10] + test_time[0:2] + test_time[3:5] + test_time[6:8]
 
# Example usage
if __name__ == "__main__":
    admission_msg = PatientAdmissionMessage(mrn='123', name='John Doe', date_of_birth='1980-01-01', sex='M')   
    discharge_msg = PatientDischargeMessage(mrn='123')
    test_result_msg = TestResultMessage(mrn='123', test_date='2021-01-01', test_time='08:00', creatinine_value=1.2)