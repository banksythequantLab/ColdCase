"""Make onnxruntime find the CUDA 12 runtime DLLs from the pip nvidia wheels.

Import this BEFORE creating any fastembed/onnxruntime session to enable GPU.
"""
import glob
import os
import site


def enable_cuda_dlls():
    added = []
    roots = site.getsitepackages() + [site.getusersitepackages()]
    for root in roots:
        for binp in glob.glob(os.path.join(root, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(binp)
                os.environ["PATH"] = binp + os.pathsep + os.environ["PATH"]
                added.append(binp)
            except OSError:
                pass
    return added


if __name__ == "__main__":
    dirs = enable_cuda_dlls()
    print(f"added {len(dirs)} nvidia dll dirs")
    from fastembed import TextEmbedding
    m = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2",
                      providers=["CUDAExecutionProvider"])
    import time
    t = time.time()
    vs = list(m.embed(["test sentence " * 20] * 256, batch_size=256))
    print(f"embedded {len(vs)} in {time.time()-t:.2f}s on GPU")
