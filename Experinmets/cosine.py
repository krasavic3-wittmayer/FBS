import numpy as np

a = np.array([1, 2, 3, 4, 5, 6, 7])
b = np.array([2, 4, 6, 8, 10])
c = np.array([3, 0, 1, 0, 3, 0, 1])

similarity = np.dot(a, c) / (
    np.linalg.norm(a) * np.linalg.norm(c)
)

print("Cosine similarity:", similarity)