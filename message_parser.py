from typing import Union

from hospital_message import PatientDischargeMessage, PatientAdmissionMessage, TestResultMessage

from prometheus_client import Counter, start_http_server

p_successful_message_parsing = Counter("successful_message_parsing", "Number of successful message parsing")

def parse_message(hl7_message_str: str) -> Union[PatientAdmissionMessage, TestResultMessage, PatientDischargeMessage]:
    """
    Parse an HL7 message string into an HL7 message object.

    Parameters:
    hl7_message_str (str): A string representation of an HL7 message.

    Returns:
    Instance of PatientAdmissionMessage, TestResultMessage, or PatientDischargeMessage.
    """
    message = hl7_message_str
    message_type = message[0].split("|")[8]
    if message_type == 'ADT^A01':
        patient_info = message[1].split("|")
        mrn = patient_info[3]
        name = patient_info[5]
        date_of_birth = patient_info[7]
        date_of_birth = patient_info[7][0:4]+"-"+patient_info[7][4:6]+"-"+patient_info[7][6:8]
        sex = patient_info[8]
        message_object = PatientAdmissionMessage(mrn, name, date_of_birth, sex)

    elif message_type == 'ORU^R01':
        mrn = message[1].split("|")[3]
        test_time = message[2].split("|")[7]
        test_day = test_time[:4]+"-"+test_time[4:6]+"-"+test_time[6:8]
        test_time = test_time[8:10]+":"+test_time[10:12]+":"+test_time[12:]
        test_result = min(float(message[3].split("|")[5]),200)
        message_object = TestResultMessage(mrn, test_day, test_time, test_result)
        
    elif message_type == 'ADT^A03': 
        mrn = message[1].split("|")[3]
        message_object = PatientDischargeMessage(mrn)
    
    else:
        raise ValueError(f"Unknown message type: {message_type}")    
    
    p_successful_message_parsing.inc()
    return message_object