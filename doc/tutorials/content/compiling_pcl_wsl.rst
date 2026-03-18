.. _compiling_pcl_wsl:

Installing Ubuntu on Windows using WSL and Compiling PCL
=========================================================

This tutorial explains how to install Ubuntu on Windows using **WSL (Windows Subsystem for Linux)**
and then how to compile and install the Point Cloud Library (PCL) inside that environment.

WSL allows you to run a genuine Ubuntu (or other Linux) environment directly on Windows, without
the overhead of a virtual machine. This makes it a convenient way to develop PCL-based applications
on Windows with a Linux toolchain.

.. note::

   WSL 2 is recommended as it provides better Linux compatibility and performance compared to WSL 1.
   The instructions below target WSL 2.

.. contents::

Requirements
------------

* Windows 10 version 2004 (Build 19041) or later, or Windows 11.
* Administrator privileges on the Windows machine.
* An internet connection to download Ubuntu and PCL dependencies.

Step 1: Enable WSL and Install Ubuntu
--------------------------------------

Open **PowerShell** or **Windows Command Prompt** as Administrator and run::

  wsl --install

This single command will:

1. Enable the required Windows optional features (Virtual Machine Platform and WSL).
2. Download and install the latest Linux kernel.
3. Set WSL 2 as the default version.
4. Download and install the **Ubuntu** distribution from the Microsoft Store.

After the command completes, **restart your computer** when prompted.

.. note::

   If you are running an older version of Windows 10 that does not support the ``wsl --install``
   command, please follow the `manual installation steps
   <https://docs.microsoft.com/en-us/windows/wsl/install-manual>`_ from the Microsoft documentation.

Choosing a specific Ubuntu version
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, ``wsl --install`` installs the latest Ubuntu LTS release. To install a specific
Ubuntu version (for example, Ubuntu 22.04), run::

  wsl --install -d Ubuntu-22.04

To list all available distributions::

  wsl --list --online

Step 2: Set Up Ubuntu
---------------------

After restarting, launch **Ubuntu** from the Start menu. The first launch will take a few minutes
to complete the initial setup. You will then be asked to create a **Unix username and password**.

Once the Ubuntu shell is open, update the package lists and upgrade existing packages::

  sudo apt update && sudo apt upgrade -y

Step 3: Install PCL Dependencies
---------------------------------

Install the required build tools and PCL dependencies::

  sudo apt install -y \
    build-essential \
    cmake \
    git \
    libboost-all-dev \
    libeigen3-dev \
    libflann-dev \
    libvtk9-dev \
    libqhull-dev \
    libopenni2-dev \
    libusb-1.0-0-dev \
    pkg-config

.. note::

   The exact VTK package name depends on the Ubuntu version installed:

   * Ubuntu 20.04 (Focal): ``libvtk7-dev``
   * Ubuntu 22.04 (Jammy): ``libvtk9-dev``
   * Ubuntu 24.04 (Noble, current LTS): ``libvtk9-dev``

   To find the available VTK package for your release, run::

     apt-cache search libvtk

Step 4: Download PCL Source Code
----------------------------------

Clone the PCL repository from GitHub::

  git clone https://github.com/PointCloudLibrary/pcl.git

Step 5: Build and Install PCL
------------------------------

Create a build directory and configure PCL with CMake::

  cd pcl && mkdir build && cd build
  cmake -DCMAKE_BUILD_TYPE=Release ..

Compile PCL (replace ``4`` with the number of CPU cores you want to use)::

  make -j4

Install PCL to the system::

  sudo make install

Step 6: Verify the Installation
--------------------------------

After installation, verify that PCL was installed correctly::

  pcl_viewer --help

You should see the PCL viewer help output.

Accessing Windows Files from WSL
----------------------------------

Your Windows drives are automatically mounted in WSL under ``/mnt/``. For example, your
``C:`` drive is accessible at ``/mnt/c/``. This allows you to work on source code stored on
your Windows filesystem::

  ls /mnt/c/Users/

.. note::

   For best I/O performance, it is recommended to store your project files inside the WSL
   filesystem (e.g., ``~/projects/``) rather than on the Windows filesystem (``/mnt/c/``).

Troubleshooting
---------------

**WSL version check**

Verify that WSL 2 is being used by running the following in PowerShell::

  wsl --list --verbose

The ``VERSION`` column should show ``2`` for your Ubuntu distribution. If it shows ``1``,
upgrade with::

  wsl --set-version Ubuntu 2

**CMake cannot find a dependency**

Make sure all required packages are installed. You can search for a package using::

  apt-cache search <package-name>

**OpenGL / visualization issues in WSL 2**

WSL 2 with Windows 11 (or Windows 10 with the WSLg feature) supports GUI applications
natively. If you encounter OpenGL issues with PCL's visualizer, ensure your GPU drivers
are up to date and that WSLg is enabled. For earlier Windows 10 versions, you may need
to install an X server such as `VcXsrv <https://sourceforge.net/projects/vcxsrv/>`_ or
`MobaXterm <https://mobaxterm.mobatek.net/>`_ and set the ``DISPLAY`` environment variable::

  export DISPLAY=:0

Next Steps
----------

* Follow the :ref:`compiling_pcl_posix` tutorial for more CMake configuration options.
* Explore the :ref:`basic_usage` tutorials to get started with PCL.
* If you prefer a fully containerized setup, see the :ref:`compiling_pcl_docker` tutorial.
