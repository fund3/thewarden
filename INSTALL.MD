# Installation Instructions

Our long term goal is to simplify this process. If you have tips on how to expedite deployment please let us know.

If you are a beginner user, don't get intimated by this process. Although it uses the command line, it shouldn't be complicated. And you may learn a thing or two.  

## Choose your path

- Quick installation: *Just follow the commands*
  - [Mac OS/X](#quick-installation-mac)
  - [Windows](#quick-installation-windows)
- Step-by-Step instructions: *detailed explanations*
  - [Mac OS/X](#step-by-step-instructions-mac-osx)
  - [Windows](#step-by-step-instructions-windows)

## Requirements

- Python 3.7 or higher
- Pip dependencies (see below)

## Quick Installation (Mac)

_This assumes you have Python 3.6+, pip, virtualenv and git already installed. If you don't, follow the step-by-step guide._

Open Terminal, navigate to where you want to store the thewarden folder and type the following:

```console
$git clone https://github.com/pxsocs/thewarden.git
$cd thewarden
$virtualenv cb_env
$source cb_env/bin/activate
$pip install -r requirements.txt
```

To start the application just execute:

```console
$python run.py
```

Finally, open a browser window and navigate to:
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

To exit just hit <kbd>ctrl</kbd>+<kbd>c</kbd> at the terminal window.

Done!

## Step-by-Step Instructions (Mac OS/X)

### Step 1 - Create a folder to store the source code

- Open Terminal (press &#x2318; + <kbd>spacebar</kbd>, then type `terminal`&#x23ce;)

- At the terminal window, create a folder to store the source code. _`~/git_clones/` is the default but feel free to change this to your preferred folder and location._

  ```console
  $mkdir ~\git_clones
  $cd ~\git_clones
  ```

### Step 2 - Install Git command line (skip if installed)

- Verify if git is already installed:
  
  ```console
  $git --status
  ```
  
  If you don't have Git installed, MacOs will prompt you to install.
  Click **Install** and follow the instructions.

  If the process above fails, try downloading Git [here](https://git-scm.com/download/mac) and follow the installation instructions.

### Step 3 - Download the source code

```console
$git clone https://github.com/pxsocs/thewarden.git
```

This will create a folder named `thewarden` and store the source code there.
Now you can review and modify the code freely. We recommend [Atom Editor](https://atom.io/) or [Visual Studio Code](https://code.visualstudio.com/) as good alternatives but feel free to use whatever you prefer.

### Step 4 - Make sure you have Python 3.7 or higher installed (skip if installed)

Make sure you have Python and that the expected version is available from your command line. You can check this by running:

```console
$python --version
```

You should get some output like  `Python 3.7.x`. If you do not have Python, please install the latest 3.x version from  [python.org](https://python.org/)  or refer to the  [Installing Python](http://docs.python-guide.org/en/latest/starting/installation/)  section of the Hitchhiker’s Guide to Python.

### Step 5 - Ensure you can run `pip` (skip if pip is installed)

Pip manages Python's libraries. These are like add-ins.  You can check if it's installed by running:

```console
$pip --version
```

If you installed Python from source, with an installer from  [python.org](https://python.org/), or via  [Homebrew](https://brew.sh/)you should already have pip. If you’re on Linux and installed using your OS package manager, you may have to install pip separately, see  [Installing pip/setuptools/wheel with Linux Package Managers](https://packaging.python.org/guides/installing-using-linux-tools/).

If  `pip`  isn’t already installed, then first try to bootstrap it from the standard library:

```console
python -m ensurepip --default-pip
```

If that still doesn’t allow you to run  `pip`:

> - Securely Download  [get-pip.py](https://bootstrap.pypa.io/get-pip.py)  [[1]](https://packaging.python.org/tutorials/installing-packages/#id7)
>
> - Run  `python  get-pip.py`.  [[2]](https://packaging.python.org/tutorials/installing-packages/#id8)  This will install or upgrade pip. Additionally, it will install  [setuptools](https://packaging.python.org/key_projects/#setuptools)  and  [wheel](https://packaging.python.org/key_projects/#wheel)  if they’re not installed already.

### Step 6 - Create a virtual environment

#### Install the virtualenv package

The virtualenv package is required to create virtual environments. You can install it with pip:

```console
$pip3 install virtualenv
```

#### Create the virtual environment

To create a virtual environment, you must specify a path. For example to create one in the local directory called cb_env, type the following:

```console
$virtualenv cb_env
```

#### Activate the virtual environment

You can activate the python environment by running the following command:

```console
$source cb_env/bin/activate
```

You should see the name of your virtual environment in brackets on your terminal line e.g. (cb_env).

Later, to deactivate the virtual environment and use your original Python environment, simply type ‘deactivate’.

```console
$deactivate
```

### Step 7 - Install the PIP packages

The list of required packages is stored on a file named `requirements.txt`. To install all the packages just type at the terminal:

```console
$pip3 install -r requirements.txt
```

### Step 8 - Start the application

To start the application just execute:

```console
$python3 run.py
```

Finally, open a browser window and navigate to:
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

To exit just hit <kbd>ctrl</kbd>+<kbd>c</kbd> at the terminal window.

Done!

-------------------------------------------------------

## Quick Installation (Windows)

_This assumes you have Python, pip, virtualenv and git already installed. If you don't, follow the step-by-step guide._

Open command prompt window, navigate to where you want to store the thewarden folder and type the following:

```console
c:\[dir]\> git clone https://github.com/pxsocs/thewarden.git
c:\[dir]\> cd thewarden
c:\[dir]\> virtualenv cb_env
c:\[dir]\> .\cb_env\Scripts\activate
c:\[dir]\> pip3 install -r requirements.txt
```

To start the application just execute:

```console
py run.py
```

Finally, open a browser window and navigate to:
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

To exit just hit <kbd>ctrl</kbd>+<kbd>c</kbd> at the terminal window.

Done!

## Step-by-Step Instructions (Windows)

### Step 1 - Create a folder to store the source code

- Open the command prompt  by clicking Start and entering `cmd` into the search field.

- At the command prompt window, create a folder to store the source code. _`c:\git_clones\` is the default but feel free to change this to your preferred folder and location._

  ```console
  c:\> md \git_clones
  c:\> cd \git_clones
  ```

### Step 2 - Install Git CMD (skip if installed)

Check if git is already installed. Should be under:

#### Start Menu -> Git -> Git CMD

 If you don't have Git installed, download Git [here](https://git-scm.com/download/win) and follow the installation instructions.

### Step 3 - Download the source code

#### Start Menu -> Git -> Git CMD

```console
c:\> cd\git_clones
c:\git_clones> git clone https://github.com/pxsocs/thewarden.git
```

This will create a folder named `thewarden` and store the source code there.
Now you can review and modify the code freely. We recommend [Atom Editor](https://atom.io/) or [Visual Studio Code](https://code.visualstudio.com/) as good alternatives but feel free to use whatever you prefer.

### Step 4 - Make sure you have Python 3.6 or higher installed (skip if installed)

Make sure you have Python and that the expected version is available from your command line. You can check this by running:

```console
c:\git_clones> py --version
```

You should get some output like  `Python 3.7x`. If you do not have Python, please install the latest 3.x version from  [python.org](https://python.org/)  or refer to the  [Installing Python](http://docs.python-guide.org/en/latest/starting/installation/)  section of the Hitchhiker’s Guide to Python.

If after installation you still can't run:

```console
c:\git_clones> py --version
```

You may need to add Python to the [PATH Environment variables]([https://www.pythoncentral.io/add-python-to-path-python-is-not-recognized-as-an-internal-or-external-command/](https://www.pythoncentral.io/add-python-to-path-python-is-not-recognized-as-an-internal-or-external-command/)).

### Step 5 - Ensure you can run `pip` (skip if pip is installed)

Pip manages Python's libraries. These are like add-ins.  You can check if it's installed by running:

```console
c:\git_clones> pip --version
```

If you installed Python from source, with an installer from  [python.org](https://python.org/), or via  [Homebrew](https://brew.sh/)you should already have pip. If you’re on Linux and installed using your OS package manager, you may have to install pip separately, see  [Installing pip/setuptools/wheel with Linux Package Managers](https://packaging.python.org/guides/installing-using-linux-tools/).

If  `pip`  isn’t already installed, then first try to bootstrap it from the standard library:

```console
c:\> python -m ensurepip --default-pip
```

If that still doesn’t allow you to run  `pip`:

> - Securely Download  [get-pip.py](https://bootstrap.pypa.io/get-pip.py)  [[1]](https://packaging.python.org/tutorials/installing-packages/#id7)
>
> - Run  `py  get-pip.py`.  [[2]](https://packaging.python.org/tutorials/installing-packages/#id8)  This will install or upgrade pip. Additionally, it will install  [setuptools](https://packaging.python.org/key_projects/#setuptools)  and  [wheel](https://packaging.python.org/key_projects/#wheel)  if they’re not installed already.

### Step 6 - Create a virtual environment

#### Install the virtualenv package

The virtualenv package is required to create virtual environments. You can install it with pip:

```console
c:> cd\git_clones\thewarden
c:\git_clones\thewarden> pip install virtualenv
```

#### Create the virtual environment

To create a virtual environment, you must specify a path. For example to create one in the local directory called ‘mypython’, type the following:

```console
c:\git_clones\thewarden> virtualenv cb_env
```

#### Activate the virtual environment

You can activate the python environment by running the following command:

```console
c:\git_clones\thewarden> .\cb_env\Scripts\activate
```

You should see the name of your virtual environment in parenthesis on your terminal line e.g. `(cb_env) c:\>`.

Later, to deactivate the virtual environment and use your original Python environment, simply type ‘deactivate’.

```console
c:\> deactivate
```

### Step 7 - Install the PIP packages

The list of required packages is stored on a file named `requirements.txt`. To install all the packages just type at the terminal:

```console
(cb_env) c:\git_clones\thewarden> pip3 install -r requirements.txt
```

### Step 8 - Start the application

To start the application just execute:

```console
(cb_env) c:\git_clones\thewarden> py run.py
```

Finally, open a browser window and navigate to:
[http://127.0.0.1:5000/](http://127.0.0.1:5000/)

To exit just hit <kbd>ctrl</kbd>+<kbd>c</kbd> at the terminal window.

Done!
