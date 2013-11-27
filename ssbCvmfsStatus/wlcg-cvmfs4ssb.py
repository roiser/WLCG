#/bin/env python

import urllib, json, datetime
from xml.parsers import expat

class c4s :

  def __init__(self):
    self.requestedVersion = '2.1.15'
    self.myVO = 'LHCb'
    self.cvmfsColumnNo = 202
    self.wlcgTopoColumnNo = 144
    self.topoDict = {'WLCG':{}, self.myVO:{}}
    self.topologyURL = 'http://lhcb-web-dirac.cern.ch/topology/lhcb_topology.xml'
    self.wlcgBaseUrl = 'http://wlcg-mon.cern.ch/dashboard/request.py/'
    self.wlcgGetUrl = self.wlcgBaseUrl+'getplotdata?columnid=%d&time=24&sites=all&batch=1'
    self.ssbMetrics = ['CvmfsVersion','CvmfsRepoRevision','CvmfsMountPoint','CvmfsCondDBMountPoint', 'CvmfsProbeTime', 'CvmfsStratumOnes', 'CvmfsNumSquids']
    self.ssbData = {}
    for k in self.ssbMetrics : self.ssbData[k] = {}


  ### start probe functions ###
  ### eval functions ###

  def evalCvmfsVersion(self, val): 
    if val == 'nfs' : return (val, 'green')
    if val == 'n/a' : return (val, 'red')
    x = 2
    maxDiff = range(x+1)
    deplV = map(lambda x: int(x), val.split('.'))
    reqV = map(lambda x: int(x), self.requestedVersion.split('.'))
    if deplV[1] == reqV[1] and deplV[0] == reqV[0] : 
      if (reqV[2] - deplV[2]) in maxDiff : return (val, 'green')
      else : return (val, 'orange')
    else : return (val, 'red')

  def evalCvmfsRepoRevision(self, val):
    return (val, 'green')

  def evalCvmfsMountPoint(self, val):
    if val and val == '/cvmfs/lhcb.cern.ch' : return (val, 'green')
    else : return (val, 'orange')

  def evalCvmfsCondDBMountPoint(self, val):
    if val == 'yes' : return (val, 'orange')
    else : return (val, 'green')

  def evalCvmfsProbeTime(self, val):
    return (val, 'green')

  def evalCvmfsStratumOnes(self, val) :
    if val : return (val, 'green')
    else: return ('none', 'red')

  def evalCvmfsNumSquids(self, val):
    if val :
      if int(val) > 1 : return (val, 'green')
      else : return (val, 'orange')
    else: return (val , 'red')

  ### retrieval functions ###

  def getValCvmfsVersion(self, site, probe, metric):
    pat1 = 'INFO: CVMFS version installed '
    pat2 = 'INFO: Mandatory mount point /cvmfs/lhcb.cern.ch is nfs mount point'
    ver = 'n/a'
    for line in probe :
      if line[:len(pat1)] == pat1 :
        ver = line[len(pat1):]
      elif line[:len(pat2)] == pat2 :
        ver = 'nfs'
    self.ssbData['CvmfsVersion'][site] = ver
    
  def getValCvmfsRepoRevision(self, site, probe, metric):
    pat = 'INFO: repository revision '
    rev = 'n/a'
    for line in probe :
      if line[:len(pat)] == pat :
        rev = line[len(pat):]
        break 
    self.ssbData['CvmfsRepoRevision'][site] = rev

  def getValCvmfsMountPoint(self, site, probe, metric):
    pat = 'INFO: Variable VO_LHCB_SW_DIR points to CVMFS mount point '
    mp = 'n/a'
    for line in probe :
      if line[:len(pat)] == pat :
        mp = line[len(pat):]
    self.ssbData['CvmfsMountPoint'][site] = mp

  def getValCvmfsCondDBMountPoint(self, site, probe, metric):
    pat = 'INFO: repository /cvmfs/lhcb-conddb.cern.ch available'
    cm = 'no'
    for line in probe :
      if line[:len(pat)] == pat :
        cm = 'yes'
    self.ssbData['CvmfsCondDBMountPoint'][site] = cm

  def getValCvmfsProbeTime(self, site, probe, metric):
    self.ssbData['CvmfsProbeTime'][site] = metric['Time']

  def getValCvmfsStratumOnes(self, site, probe, metric) :
    strats = []
    pat = 'INFO: Servers: '
    for line in probe :
      if line[:len(pat)] == pat :
        stratumL = line[len(pat):]
        for serv in stratumL.split() :
          strats.append('.'.join(serv.split('/')[2].split(':')[0].split('.')[-2:]))
        break
    self.ssbData['CvmfsStratumOnes'][site] = ' '.join(strats)

  def getValCvmfsNumSquids(self, site, probe, metric) :
    numSq = 0
    pat = 'INFO: Proxies: '
    for line in probe :
      if line[:len(pat)] == pat :
        numSq = len(line[len(pat):].split())
        break
    self.ssbData['CvmfsNumSquids'][site] = numSq

  ### end probe functions ####


  def populateTopology(self):
    topo = json.loads(urllib.urlopen(self.wlcgGetUrl%self.wlcgTopoColumnNo).read())
    for ent in topo['csvdata'] : self.topoDict[self.myVO][ent['SiteId']] = ent['Status']

  def collectInfo(self):
    info = json.loads(urllib.urlopen(self.wlcgGetUrl%self.cvmfsColumnNo).read())
    for metricInf in info['csvdata'] :
      site = self.topoDict[self.myVO][metricInf['SiteId']]
      tl = urllib.urlopen(self.wlcgBaseUrl+metricInf['URL']).read().split('\n')
      for metr in self.ssbMetrics : eval('self.getVal'+metr)(site, tl, metricInf)
              
  def writeSSBColumns(self):
    for k in self.ssbMetrics :
      fun = 'self.eval'+k
      colData = self.ssbData[k]
      f = open(k+'.ssb.txt', 'w')
      for site in colData.keys() :
        now = str(datetime.datetime.now())
        (val, color) = eval(fun)(colData[site])
        url = 'http://localhost'
        f.write('%s\t%s\t%s\t%s\t%s\n' % (now, site, val, color, url))
      f.close()

  def createWLCGLHCbMapping(self):
    f = open('WLCGSiteMapping.ssb.txt','w')
    for site in self.topoDict['WLCG'].keys() :
      now = str(datetime.datetime.now())
      val = self.topoDict['WLCG'][site]
      color = 'green'
      url = 'http://localhost'
      f.write('%s\t%s\t%s\t%s\t%s\n' % (now, site, val, color, url))

  def xmlStartElement(self, name, attrs):
    if name == 'atp_site' : self.currWLCGSite = attrs['name']
    if name == 'group' and attrs['type'] == 'LHCb_Site' : 
      self.topoDict['WLCG'][attrs['name']] = self.currWLCGSite

  def parseXmlTopology(self) :
    topo = urllib.urlopen(self.topologyURL).read()
    p = expat.ParserCreate()
    p.StartElementHandler = self.xmlStartElement
    p.Parse(topo)

  def run(self):
    self.parseXmlTopology()
    self.populateTopology()
    self.collectInfo()
    self.writeSSBColumns()
    self.createWLCGLHCbMapping()

if __name__ == '__main__' :
  c4s().run()
