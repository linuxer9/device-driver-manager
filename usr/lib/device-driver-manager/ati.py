#!/usr/bin/env python

import os
import re
import functions
from execcmd import ExecCmd

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']
atiStartSerie = 5000


class ATI():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.hw = functions.getGraphicsCard()

        # Test
        #self.hw = '01:00.0 VGA compatible controller [0300]: Advanced Micro Devices [AMD] nee ATI Manhattan [Mobility Radeon HD 5400 Series] [1002:68e0]'

    # Called from drivers.py: Check for ATI
    def getATI(self):
        # Check for ATI cards
        hwList = []
        # Is it ATI?
        nvChk = re.search('\\b' + hwCodes[1] + '\\b', self.hw.lower())
        if nvChk:
            self.log.write('ATI card found: ' + self.hw, 'ati.getATI', 'info')
            # Get the ATI chip set serie
            atiSerie = re.search('\s\d{4,}', self.hw)
            if atiSerie:
                self.log.write('ATI chip serie found: ' + atiSerie.group(0), 'ati.getATI', 'info')
                intSerie = functions.strToNumber(atiSerie.group(0))
                # Only add series from atiStartSerie
                if intSerie >= atiStartSerie:
                    drv = self.getDriver()
                    status = functions.getPackageStatus(drv)
                    self.log.write('ATI ' + drv + ' status: ' + status, 'ati.getATI', 'debug')
                    hwList.append([self.hw, hwCodes[1], status])
                else:
                    self.log.write('ATI chip serie not supported: ' + str(intSerie), 'ati.getATI', 'warning')
                    hwList.append([self.hw, hwCodes[1], packageStatus[2]])
            else:
                self.log.write('No ATI chip serie found: ' + self.hw, 'ati.getATI', 'warning')
                hwList.append([self.hw, hwCodes[1], packageStatus[2]])

        return hwList

    # Check distribution and get appropriate driver
    def getDriver(self):
        drv = ''
        if self.distribution == 'debian':
            drv = 'fglrx-driver'
        else:
            drv = 'fglrx'
        return drv

    # Get additional packages
    # The second value in the list is a numerical value:
    # 0 = Need to install, but removal before reinstallation is not needed
    # 1 = Need to install and removal is needed before reinstallation
    # 2 = Optional install
    def getAdditionalPackages(self, driver):
        drvList = []
        # Get the correct linux header package
        linHeader = functions.getLinuxHeadersAndImage()
        drvList.append([linHeader[0], 0])
        # Common packages
        if self.distribution == 'debian':
            drvList.append(['build-essential', 0])
            drvList.append(['module-assistant', 0])
            drvList.append([driver, 1])
            drvList.append(['fglrx-modules-dkms', 1])
            drvList.append(['libgl1-fglrx-glx', 1])
            drvList.append(['glx-alternative-fglrx', 0])
            drvList.append(['fglrx-control', 1])
            drvList.append(['fglrx-glx-ia32', 2])
        else:
            drvList.append([driver, 1])
            drvList.append(['fglrx-amdcccle', 1])
        return drvList

    # Install the given packages
    def installATIDriver(self, packageList):
        try:
            # Remove certain packages before installing the drivers
            for package in packageList:
                if package[1] == 1:
                    if functions.isPackageInstalled(package[0]):
                        self.log.write('Remove package: ' + package[0], 'ati.installATIDriver', 'debug')
                        self.ec.run('apt-get -y --force-yes remove ' + package[0])

            # Preseed answers for some packages
            self.preseedATIPackages('install')

            # Install the packages
            installString = ''
            notInRepo = ''
            for package in packageList:
                chkStatus = functions.getPackageStatus(package[0])
                if chkStatus != packageStatus[2]:
                    installString += ' ' + package[0]
                elif package[1] != 2:
                    notInRepo += ', ' + package[0]

            if notInRepo == '':
                self.ec.run('apt-get -y --force-yes install' + installString)
            else:
                self.log.write('Install aborted: not in repository: ' + notInRepo[2:], 'ati.installATIDriver', 'error')

        except Exception, detail:
            self.log.write(detail, 'ati.installATIDriver', 'exception')

    # Called from drivers.py: install the ATI drivers
    def installATI(self):
        try:
            # Install the driver and create xorg.conf
            drv = self.getDriver()
            if drv != '':
                self.log.write('ATI driver to install: ' + drv, 'ati.installATI', 'info')
                packages = self.getAdditionalPackages(drv)
                self.installATIDriver(packages)
                # Configure ATI
                xorg = '/etc/X11/xorg.conf'
                if os.path.exists(xorg):
                    self.log.write('Copy ' + xorg + ' to ' + xorg + '.ddm.bak', 'ati.installATI', 'info')
                    self.ec.run('cp ' + xorg + ' ' + xorg + '.ddm.bak')
                self.log.write('Configure ATI', 'ati.installATI', 'debug')
                self.ec.run('aticonfig --initial -f')

                self.log.write('Done installing ATI drivers', 'ati.installATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.installATI', 'exception')

    # Called from drivers.py: remove the ATI drivers and revert to Nouveau
    def removeATI(self):
        try:
            self.log.write('Remove ATI drivers: fglrx', 'ati.removeATI', 'debug')

            # Preseed answers for some packages
            self.preseedATIPackages('purge')

            self.ec.run('apt-get -y --force-yes purge fglrx*')
            self.ec.run('apt-get -y --force-yes autoremove')
            self.ec.run('apt-get -y --force-yes install xserver-xorg-video-radeon xserver-xorg-video-nouveau xserver-xorg-video-ati libgl1-mesa-glx libgl1-mesa-dri libglu1-mesa')

            # Rename xorg.conf
            xorg = '/etc/X11/xorg.conf'
            if os.path.exists(xorg):
                self.log.write('Rename : ' + xorg + ' -> ' + xorg + '.ddm.bak', 'nvidia.removeNvidia', 'debug')
                os.rename(xorg, xorg + '.ddm.bak')

            self.log.write('Done removing ATI drivers', 'ati.removeATI', 'info')

        except Exception, detail:
            self.log.write(detail, 'ati.removeATI', 'exception')

    def preseedATIPackages(self, action):
        if self.distribution == 'debian':
            # Run on configured system and debconf-utils installed:
            # debconf-get-selections | grep fglrx > debconf-fglrx.seed
            # replace tabs with spaces and change the default answers (note=space, boolean=true or false)
            debConfList = []
            debConfList.append('libfglrx fglrx-driver/check-for-unsupported-gpu boolean false')
            debConfList.append('fglrx-driver fglrx-driver/check-xorg-conf-on-removal boolean false')
            debConfList.append('libfglrx fglrx-driver/install-even-if-unsupported-gpu-exists boolean false')
            debConfList.append('fglrx-driver fglrx-driver/removed-but-enabled-in-xorg-conf note ')
            debConfList.append('fglrx-driver fglrx-driver/needs-xorg-conf-to-enable note ')

            # Add each line to the debconf database
            for line in debConfList:
                os.system('echo "' + line + '" | debconf-set-selections')

            # Install or remove the packages
            self.ec.run('apt-get -y --force-yes ' + action + ' libfglrx fglrx-driver')
