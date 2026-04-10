import numpy as np

def calculate_psnr(img1, img2, max_val=255):
    # Convert images to float to avoid overflow/underflow
    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)
    
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')  # Identical images
    
    # PSNR Formula: 20 * log10(MAX / sqrt(MSE))
    return 20 * np.log10(max_val / np.sqrt(mse))
