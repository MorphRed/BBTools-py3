import platform

try:
    import astor
except ImportError:
    if platform.system() == "Linux":
        print("This script requires the 'astor' package to be installed. Install it through your distro's package manager or pip")
    else:
        print("This script requires the 'astor' package to be installed. Do 'pip install astor' to install it.")
    exit(1)
    
if astor.__version__ != "0.8.1":
    print('\033[93m' + 'Not using the recommended version of astor (0.8.1), currently using: ' + astor.__version__ + '\033[0m\n')