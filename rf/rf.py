
import numpy as np


def s_real_imag_to_mag_angle(sParameters):
    # Check the shape of sParameters to determine the layout
    if sParameters.shape[0] == 2:  # sParameters[0, :] is real, sParameters[1, :] is imaginary
        real_part = sParameters[0, :]
        imag_part = sParameters[1, :]
    else:  # Assuming sParameters[:, 0, :] is real and sParameters[:, 1, :] is imaginary
        real_part = sParameters[:, 0, :]
        imag_part = sParameters[:, 1, :]
    
    # Calculate magnitude
    magnitude = np.sqrt(real_part**2 + imag_part**2)
    
    # Calculate angle in degrees
    angle = np.degrees(np.arctan2(imag_part, real_part))
    
    return magnitude, angle

def s_real_imag_to_db_angle(sParameters):
    magnitude, angle = s_real_imag_to_mag_angle(sParameters)
    
    # Convert magnitude to dB
    magnitude_db = 20 * np.log10(magnitude)
    
    return magnitude_db, angle

def s_real_imag_to_z_real_imag(sParameters, Z0=50):
    # Check the shape of sParameters to determine the layout
    if sParameters.shape[0] == 2:  # sParameters[0, :] is real, sParameters[1, :] is imaginary
        S = sParameters[0, :] + 1j * sParameters[1, :]
    else:  # Assuming sParameters[:, 0, :] is real and sParameters[:, 1, :] is imaginary
        S = sParameters[:, 0, :] + 1j * sParameters[:, 1, :]
    
    # Calculate Z
    Z = Z0 * (1 + S) / (1 - S)
    
    # Separate into real and imaginary parts
    Z_real = np.real(Z)
    Z_imag = np.imag(Z)
    
    return Z_real, Z_imag








# def extract_s_parameters_real_imaginary(s_parameters):
#     # Get the shape
#     shape = np.shape(s_parameters)
    
#     # Calculate number of ports
#     num_ports = int(np.sqrt(shape[1] / 2))
    
#     # List to store extracted values
#     extracted_values = []

#     # Access S-parameter values
#     for idx in range(shape[0]):
#         data_set = {
#             "num_ports": num_ports
#         }
#         for port1 in range(num_ports):
#             for port2 in range(num_ports):
#                 s_index = 2 * (port1 * num_ports + port2)
#                 real_values = s_parameters[idx][s_index]
#                 imag_values = s_parameters[idx][s_index + 1]
                
#                 key = f"S{port1+1}{port2+1}"
#                 data_set[key] = {
#                     "real": real_values,
#                     "imag": imag_values
#                 }
#         extracted_values.append(data_set)

#     return extracted_values




# def extract_s_parameters_complex(s_parameters):
#     # Get the shape
#     shape = np.shape(s_parameters)
    
#     # Calculate number of ports
#     num_ports = int(np.sqrt(shape[1] / 2))
    
#     # List to store extracted values
#     extracted_values = []

#     # Access S-parameter values
#     for idx in range(shape[0]):
#         data_set = {
#             "num_ports": num_ports
#         }
#         for port1 in range(num_ports):
#             for port2 in range(num_ports):
#                 s_index = 2 * (port1 * num_ports + port2)
#                 real_values = s_parameters[idx][s_index]
#                 imag_values = s_parameters[idx][s_index + 1]
                
#                 complex_values = real_values + 1j * imag_values
                
#                 key = f"S{port1+1}{port2+1}"
#                 data_set[key] = complex_values
                
#         extracted_values.append(data_set)

#     return extracted_values



# def extract_s_parameters_magnitude_angle(s_parameters):
#     # Get the shape
#     shape = np.shape(s_parameters)
    
#     # Calculate number of ports
#     num_ports = int(np.sqrt(shape[1] / 2))
    
#     # List to store extracted values
#     extracted_values = []

#     # Access S-parameter values
#     for idx in range(shape[0]):
#         data_set = {
#             "num_ports": num_ports
#         }
#         for port1 in range(num_ports):
#             for port2 in range(num_ports):
#                 s_index = 2 * (port1 * num_ports + port2)
#                 magnitude = s_parameters[idx][s_index]
#                 angle_degrees = s_parameters[idx][s_index + 1]
                
#                 key = f"S{port1+1}{port2+1}"
#                 data_set[key] = {
#                     "magnitude": magnitude,
#                     "angle_degrees": angle_degrees
#                 }
#         extracted_values.append(data_set)

#     return extracted_values


# def extract_s_parameters_db_angle(s_parameters):
#     # Get the shape
#     shape = np.shape(s_parameters)
    
#     # Calculate number of ports
#     num_ports = int(np.sqrt(shape[1] / 2))
    
#     # List to store extracted values
#     extracted_values = []

#     # Access S-parameter values
#     for idx in range(shape[0]):
#         data_set = {
#             "num_ports": num_ports
#         }
#         for port1 in range(num_ports):
#             for port2 in range(num_ports):
#                 s_index = 2 * (port1 * num_ports + port2)
#                 db = s_parameters[idx][s_index]
#                 angle_degrees = s_parameters[idx][s_index + 1]
                
#                 key = f"S{port1+1}{port2+1}"
#                 data_set[key] = {
#                     "db": db,
#                     "angle_degrees": angle_degrees
#                 }
#         extracted_values.append(data_set)

#     return extracted_values