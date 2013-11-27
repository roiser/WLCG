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
    self.ssbColumns = {'INFO: CVMFS version installed ' : 'CvmfsVersion',
                       'INFO: repository revision ' : 'CvmfsRepoRevision',
                       'INFO: Variable VO_LHCB_SW_DIR points to CVMFS mount point ' : 'CvmfsMountPoint',
                       'INFO: repository /cvmfs/lhcb-conddb.cern.ch availabl' : 'CvmfsCondDBMountPoint',
                       'INFO: Mandatory mount point /cvmfs/lhcb.cern.ch is nfs mount poin' : 'CvmfsViaNfs'
                       }
    self.usedSites = []
    self.ssbData = {}
    for k in self.ssbColumns.keys() : self.ssbData[self.ssbColumns[k]] = {}


  def evalCvmfsViaNfs(self, val):
    if val and val == 't' : return ('nfs', 'green')

  def evalCvmfsVersion(self, val): 
    if val == 'vmfs/lhcb.cern.ch is nfs mount point' : return ('nfs', 'green')
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
    if val and val == 'e' : return ('yes', 'orange')
    else : return ('no', 'green')



  def populateTopology(self):
    topo = json.loads(urllib.urlopen(self.wlcgGetUrl%self.wlcgTopoColumnNo).read())
    for ent in topo['csvdata'] : self.topoDict[self.myVO][ent['SiteId']] = ent['Status']

  def collectInfo(self):
    matchLines = self.ssbColumns.keys()
    info = json.loads(urllib.urlopen(self.wlcgGetUrl%self.cvmfsColumnNo).read())
    for metric in info['csvdata'] :
      itemFound = []
      site = self.topoDict[self.myVO][metric['SiteId']]
      tinfo = urllib.urlopen(self.wlcgBaseUrl+metric['URL']).read()
      for tl in tinfo.split('\n') :
        for ml in matchLines :
          if tl[:len(ml)] == ml :
            if self.ssbColumns[ml] == 'CvmfsViaNfs' : ml = 'INFO: CVMFS version installed '
            #if not self.ssbData[self.ssbColumns[ml]].has_key(site) :
            if self.ssbColumns[ml] not in itemFound : 
              itemFound.append(self.ssbColumns[ml])
              self.ssbData[self.ssbColumns[ml]][site] = tl[len(ml):]
              if site not in self.usedSites : self.usedSites.append(site)
              
  def writeSSBColumns(self):
    for k in self.ssbData.keys() :
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
    for site in self.topoDict['WLCG'].keys() : # self.usedSites :
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
