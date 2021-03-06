#!/usr/bin/env python

import os
import functions
from execcmd import ExecCmd

packageStatus = ['installed', 'notinstalled', 'uninstallable']
hwCodes = ['nvidia', 'ati', 'broadcom', 'pae', 'mirror']


class PAE():

    def __init__(self, distribution, loggerObject):
        self.distribution = distribution.lower()
        self.distributionReleaseNumber = functions.getDistributionReleaseNumber()
        self.log = loggerObject
        self.ec = ExecCmd(self.log)
        self.packages = functions.getLinuxHeadersAndImage(True, 'pae$', '-rt')

    # Check if the PAE kernel can be installed
    def getPae(self):
        hwList = []

        # Ubuntu is already PAE enabled from version 12.10 (Quantal) and LM 14 Nadia is based on Quantal: no need to check
        # https://help.ubuntu.com/community/EnablingPAE
        self.log.write('Distribution: ' + self.distribution + ' ' + str(self.distributionReleaseNumber), 'pae.getPae', 'debug')
        skipPae = False
        if (self.distribution == 'linuxmint' and self.distributionReleaseNumber >= 14) or (self.distribution == 'ubuntu' and self.distributionReleaseNumber >= 12.10):
            skipPae = True

        if not skipPae:
            # Get the kernel release
            kernelRelease = self.ec.run('uname -r')
            # Check the machine hardware
            machine = self.ec.run('uname -m')

            if not 'amd64' in kernelRelease[0]:
                if not 'pae' in kernelRelease[0]:
                    self.log.write('Single-core kernel found: ' + kernelRelease[0], 'pae.getPae', 'debug')

                    # Get #CPU's: cat /proc/cpuinfo | grep processor | wc -l
                    if machine[0] == 'i686':
                        self.log.write('Multi-core system running single-core kernel found', 'pae.getPae', 'info')
                        # Check package status
                        status = packageStatus[0]
                        for package in self.packages:
                            if not functions.isPackageInstalled(package):
                                self.log.write('PAE not installed', 'pae.getPae', 'info')
                                status = packageStatus[1]
                                break
                        hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], status])
                    elif machine[0] == 'x86_64':
                        self.log.write('PAE skipped: 64-bit system', 'pae.getPae', 'debug')
                    else:
                        self.log.write('PAE kernel cannot be installed: single-core system', 'pae.getPae', 'warning')

                else:
                    self.log.write('Multi-core already installed: ' + kernelRelease[0], 'pae.getPae', 'info')
                    hwList.append(['Multi-core support for 32-bit systems', hwCodes[3], packageStatus[0]])

        return hwList

    # Called from drivers.py: install PAE kernel
    def installPAE(self):
        try:
            cmdPae = 'apt-get -y --force-yes install'
            for package in self.packages:
                cmdPae += ' ' + package
            self.log.write('PAE kernel install command: ' + cmdPae, 'pae.installPAE', 'debug')
            self.ec.run(cmdPae)

            # Rename xorg.conf
            xorg = '/etc/X11/xorg.conf'
            if os.path.exists(xorg):
                self.log.write('Rename : ' + xorg + ' -> ' + xorg + '.ddm.bak', 'pae.installPAE', 'debug')
                os.rename(xorg, xorg + '.ddm.bak')

            self.log.write('Done installing PAE', 'pae.installPAE', 'info')

        except Exception, detail:
            self.log.write(detail, 'pae.installPAE', 'error')

    # Called from drivers.py: remove the PAE kernel
    # TODO: I don't think this is going to work - test this
    def removePAE(self):
        try:
            kernelRelease = self.ec.run('uname -r')
            if not 'pae' in kernelRelease[0]:
                self.log.write('Not running pae, continue removal', 'pae.removePAE', 'debug')
                for package in self.packages:
                    cmdPurge = 'apt-get -y --force-yes purge ' + package
                    self.log.write('PAE package to remove: ' + package, 'pae.removePAE', 'info')
                    self.ec.run(cmdPurge)
                self.ec.run('apt-get -y --force-yes autoremove')
                self.log.write('Done removing PAE', 'pae.removePAE', 'info')
            else:
                self.log.write('Cannot remove PAE when running PAE', 'pae.removePAE', 'warning')

        except Exception, detail:
            self.log.write(detail, 'pae.removePAE', 'error')
