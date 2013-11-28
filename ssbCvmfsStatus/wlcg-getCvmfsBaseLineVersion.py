#!/bin/env python

import urllib, re, os
from xml.parsers import expat

class blv :

  def __init__(self):
    self.baseUrl = 'https://twiki.cern.ch/twiki/bin/view/LCG/WLCGBaselineVersions'
    self.nextIsVersion = False
    self.oldCvmfsVersion = ''
    self.newCvmfsVersion = ''
    self.cvmfsVersionFile = 'cvmfsVersion.txt'

  def xmlCharElement(self, data):
    if self.newCvmfsVersion : return
    if self.nextIsVersion : self.newCvmfsVersion = re.subn('\s','',data)[0]
    elif repr(data).find('CernVM-FS') != -1 : self.nextIsVersion = True
      
  def doIt(self) :
    if os.path.isfile(self.cvmfsVersionFile) :
      f = open(self.cvmfsVersionFile, 'r')
      self.oldCvmfsVersion = f.read().replace('\n','')
      if not self.oldCvmfsVersion : print "File %s has no content" % self.cvmfsVersionFile
      f.close()
    
    baseTxt = urllib.urlopen(self.baseUrl).read()
    p = expat.ParserCreate()
    p.CharacterDataHandler = self.xmlCharElement
    try : p.Parse(baseTxt)
    except expat.ExpatError : pass

    if self.newCvmfsVersion :
      if self.oldCvmfsVersion != self.newCvmfsVersion :
        print "Baseline CVMFS Version has changed, old version %s, new version %s" % (self.oldCvmfsVersion, self.newCvmfsVersion)
        f = open(self.cvmfsVersionFile, 'w')
        f.write(self.newCvmfsVersion)
        f.close()
    else :
      print "Could not find CVMFS version information in file %s" % self.baseUrl

  def run(self):
    self.doIt()


if __name__ == '__main__' : blv().run()
