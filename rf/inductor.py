import numpy as np



def s_real_imag_to_q_and_l(sParameters, f, Z0=50):
    # Check the shape of sParameters to determine the layout
    if sParameters.shape[0] == 2:  # sParameters[0, :] is real, sParameters[1, :] is imaginary
        S = sParameters[0, :] + 1j * sParameters[1, :]
    else:  # Assuming sParameters[:, 0, :] is real and sParameters[:, 1, :] is imaginary
        S = sParameters[:, 0, :] + 1j * sParameters[:, 1, :]
    
    
    # Define two complex numbers
    a = np.array([1 + 2j])
    b = np.array([1 - 1j])

    # Divide the two complex numbers
    result = a / b

    print(result)  # [1.5+0.5j]
    
    # Calculate Z
    Z = Z0 * (1 + S) / (1 - S)
    
    # Calculate Q using Z
    Q = np.imag(Z) / np.real(Z)
    
    # Calculate L from imaginary part of Z
    XL = np.imag(Z)
    L = XL / (2 * np.pi * f)
    
    return Q, L


def s_real_imag_to_q_and_l_2(sParameters, f, Z0=50):
    # Check the shape of sParameters to determine the layout
    if sParameters.shape[0] == 2:  # sParameters[0, :] is real, sParameters[1, :] is imaginary
        S = sParameters[0, :] + 1j * sParameters[1, :]
    else:  # Assuming sParameters[:, 0, :] is real and sParameters[:, 1, :] is imaginary
        S = sParameters[:, 0, :] + 1j * sParameters[:, 1, :]
    
    # Calculate Z
    Z = Z0 * (1 + S) / (1 - S)
    
    # Calculate Y
    Y = 1.0 / Z
    
    # Calculate Q
    Q = - np.imag(Y) / np.real(Y)
    
    # Calculate L from imaginary part of Z
    XL = np.imag(Z)
    L = XL / (2 * np.pi * f)
    
    return Q, L