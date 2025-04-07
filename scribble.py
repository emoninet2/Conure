import numpy as np

# Load data
data = np.load('/mnt/storage/conure_data/tsmc65/inductors/Inductor_Coplanar_1N_to_5N.npz')
s_params = data['sParameters']
design_params = data['designParameters']
Z0 = 50

# Reconstruct frequency axis
freq = np.linspace(1e6, 50e9, s_params.shape[2])  # (2000,)
omega = 2 * np.pi * freq

# Find index closest to 15 GHz
target_freq = 15e9
idx_15GHz = np.argmin(np.abs(freq - target_freq))

# Convert S11 to complex S-parameter and compute impedance
S11 = s_params[:, 0, :] + 1j * s_params[:, 1, :]  # (4950, 2000)
Z = Z0 * (1 + S11) / (1 - S11)  # (4950, 2000)

# Calculate L and Q at 15 GHz
L_15GHz = np.imag(Z[:, idx_15GHz]) / omega[idx_15GHz]
Q_15GHz = np.imag(Z[:, idx_15GHz]) / np.real(Z[:, idx_15GHz])

# Filter around L ≈ 2nH at 15 GHz
target_L = 2.25e-9
tolerance = 0.05e-9
mask = np.abs(L_15GHz - target_L) <= tolerance
matching_indices = np.where(mask)[0]

# Print matching samples with Z11 real and imaginary parts
for idx in matching_indices:
    print(f"Sample {idx}")
    print(f"  Inductance @ 15 GHz: {L_15GHz[idx]*1e9:.3f} nH")
    print(f"  Q @ 15 GHz: {Q_15GHz[idx]:.2f}")
    print(f"  Z₁₁ @ 15 GHz: {np.real(Z[idx, idx_15GHz]):.2f} + j{np.imag(Z[idx, idx_15GHz]):.2f} Ω")
    print(f"  Design Parameters: {design_params[idx]}")
    print("-" * 50)

exit()
