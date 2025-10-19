import os, json, subprocess, sys

def run(cmd, file):
    print(f"Running {cmd} on {file}")
    proc = subprocess.run(
        [sys.executable, cmd],
        stdin=open(file, "rb"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.stderr:
        print("stderr:", proc.stderr.decode())
    print(proc.stdout.decode())

if __name__ == "__main__":
    os.system("python gen_factory.py")
    os.system("python gen_belts.py")
    run("factory/main.py", "sample_factory_input.json")
    run("belts/main.py", "sample_belt_input.json")
