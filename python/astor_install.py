import platform

try:
    import astor
except ImportError:
    if platform.system() == "Linux":
        print("This script requires 'astor' to be installed. Install it through your distro's package manager")
    else:
        print("This script requires 'astor' to be installed. Do 'pip install astor' to install it.")
    exit(1)
    
if astor.__version__ != "0.8.1":
    print('Not using the recommended version of astor, currently using: ' + astor.__version__)